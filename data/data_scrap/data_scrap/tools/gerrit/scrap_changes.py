import asyncio
import atexit
import json
import logging
import os
import random
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import fire
import psycopg2
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer

# Configure logging to display the date and time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

beijing_tz = timezone(timedelta(hours=8))

logging.info(
    f'gerrit scraper script started at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
)

_pg_uri = os.getenv('SCRAP_DB_URI')
_gerrit_user = os.getenv('GERRIT_USER')
_target_topic = os.getenv('TARGET_TOPIC')

_gerrit_query_interval = 3  # query every 3 seconds

_bootstrap_servers = '10.134.11.122:9092,10.134.11.121:9092,10.134.11.120:9092'

_kafka_producer_config = {
    'bootstrap.servers': _bootstrap_servers,
    # 1MB, max size of starrocks column is 1MB
    'message.max.bytes': 1000 * 1000,
}

_kafka_consumer_config = {
    'bootstrap.servers': _bootstrap_servers,
    'group.id': 'prod.gerrit-scraper',
    'enable.auto.commit': False,
    'auto.offset.reset': 'latest',
}

_gerrit_event_topics = ['gerrit-event']

# 线程停止标志
_stop_event_consuming = threading.Event()

_producer = Producer(**_kafka_producer_config)
_consumer = Consumer(**_kafka_consumer_config)
_consumer.subscribe(_gerrit_event_topics)

_gerrit_server_instances = {
    'gerrit-master-1': {
        'port': '40101',
        'host': '10.134.86.224',
    },
    'gerrit-master-2': {
        'port': '40102',
        'host': '10.134.86.224',
    },
}


def batch_consume_messages(consumer, batch_size, timeout, callback):
    msg_list = consumer.consume(num_messages=batch_size, timeout=timeout)
    for msg in msg_list:
        topic = msg.topic()
        partition = msg.partition()
        offset = msg.offset()
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                logging.info(
                    f'topic {topic} partition {partition} reached end at offset {offset}'
                )
            else:
                raise KafkaException(msg.error())
        else:
            try:
                msg_str = msg.value().decode('utf-8')
            except Exception as e:
                logging.error(f'failed to decode message: {msg.value()}')
                raise e
            callback(msg_str, topic=topic, partition=partition, offset=offset)
    # commit all, if there is error duing processing, it won't commit anyone
    # so messages maybe consumed many times
    consumer.commit(asynchronous=True)


def upsert_gerrit_change(change_number, project, private, event_type, event_at):
    sql = """
    INSERT INTO gerrit_change_task_queue (change_id, repo, private, event_type, last_event_at)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (change_id, repo)
    DO UPDATE
        SET last_event_at = excluded.last_event_at
            ,private=excluded.private
            ,event_type=excluded.event_type
            ,continuous_failed_count = 0 -- 有新的事件进来就归零，需要重新采集
    """
    execute_sql(sql, (change_number, project, private, event_type, event_at),
                True)


def handle_gerrit_event(msg_str, topic=None, partition=None, offset=None):
    '''gerrit event types:
    private-state-changed
    change-restored
    wip-state-changed
    patchset-created
    project-created
    ref-replicated
    hashtags-changed
    reviewer-added
    ref-replication-scheduled
    ref-updated
    vote-deleted
    comment-added
    change-merged
    change-abandoned
    topic-changed
    reviewer-deleted
    fetch-ref-replicated
    change-deleted
    ref-replication-done
    '''
    # Log event reception randomly (approximately 10% of the time) to reduce log volume
    if random.random() < 0.1:
        logging.info(f'received gerrit event @ {topic}:{partition}:{offset}')
    msg = json.loads(msg_str)
    type_ = msg.get('type')
    project = msg.get('project')
    event_created_on = msg.get('eventCreatedOn')  # unix seconds
    event_at = datetime.fromtimestamp(event_created_on, beijing_tz).isoformat()
    change = msg.get('change', {})
    change_number = change.get('number')
    private = bool(change.get('private'))
    if project and event_at and change_number:
        logging.info(
            f'gerrit event type: {type_}, project: {project}, change number: {change_number}, event created on: {event_at}'
        )
        upsert_gerrit_change(change_number, project, private, type_, event_at)


def event_consuming_loop():
    """
    Kafka事件消费循环 - 运行在独立线程中
    """
    logging.info('Kafka event consuming loop started in separate thread')
    while not _stop_event_consuming.is_set():
        try:
            # 检查停止标志，如果设置了则退出
            if _stop_event_consuming.wait(0.1):  # 等待0.1秒或直到停止标志被设置
                break
            batch_consume_messages(_consumer, 200, 5, handle_gerrit_event)
        except Exception as e:
            logging.error(f'failed to consume messages: {e}')
            if not _stop_event_consuming.wait(1):  # 出错时等待1秒再重试，除非收到停止信号
                continue
            else:
                break

    logging.info('Kafka event consuming loop stopped')


def execute_sql(sql, args=None, commit=False):
    if not args:
        args = tuple()
    conn = None
    try:
        logging.info(f'will execute sql: {sql}, with args: {args}')
        conn = psycopg2.connect(_pg_uri)
        cur = conn.cursor()
        cur.execute(sql, args)

        if commit:
            conn.commit()

        if not cur.description:
            return
        if hasattr(cur, 'rowcount'):
            logging.info(f'cur.rowcount {cur.rowcount}')
        col_names = [desc.name for desc in cur.description]
        results = cur.fetchall()
        logging.info(f'get {len(results)} results')
        rows = [dict(zip(col_names, row)) for row in results]
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        logging.error(
            f'failed to execute sql: {sql}, with args: {args}, error: {e}')
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


async def get_gerrit_change_detail(change_id, repo, host, port):
    # Build the SSH command as a list of arguments
    ssh_command = [
        'ssh',
        '-p',
        port,  # '29418' gerrit ssh port
        f'{_gerrit_user}@{host}',  # gerrit.it.chehejia.com
        'gerrit',
        'query',
        '--current-patch-set',
        f'change:{change_id}',
        f'repo:{repo}',
        '--all-approvals',
        '--all-reviewers',
        '--comments',
        '--commit-message',
        '--files',
        '--format',
        'JSON'
    ]

    # Run the SSH command using subprocess.Popen
    try:
        logging.info(f'will execute ssh command: {ssh_command}')
        await asyncio.sleep(_gerrit_query_interval)
        proc = subprocess.Popen(ssh_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        stdout, stderr = proc.communicate()

        if proc.returncode == 0:
            # Each line of the output will be a separate JSON object, so we process line by line.
            for line in stdout.strip().split('\n'):
                # Parse the JSON output
                json_data = json.loads(line)
                logging.info(f'get change: {json_data.get("number")}')
                # 如果没有获取到change时返回的json不一样，获取到change时里面没有 rowCount
                if 'rowCount' in json_data and json_data['rowCount'] == 0:
                    return None, 0
                return json_data, len(line)
        else:
            # Handle errors if the command didn't succeed
            print("Error running SSH command:", stderr)
    except Exception as e:
        # Handle any other exceptions
        print("An exception occurred:", str(e))
    return None, 0


async def get_best_gerrit_change_detail(change_id, repo):
    '''gerrit 双master不一致问题太验证了，这里采取这样的方式取数，
    从所有节点都获取一次，去返回的数据长度最大的那个'''
    best_result = None, 0
    best_instance = None
    instance_length_map = {}
    for instance, instance_config in _gerrit_server_instances.items():
        gerrit_port = instance_config['port']
        gerrit_host = instance_config['host']
        logging.info(f'change {change_id} fetch from instance {instance}')
        result = await get_gerrit_change_detail(change_id, repo, gerrit_host,
                                                gerrit_port)
        instance_length_map[instance] = result[1]
        if result[1] >= best_result[1]:
            best_instance = instance
            best_result = result
    logging.info(
        f'change {change_id} best instance is {best_instance}, len: {best_result[1]}'
    )
    for instance, length in instance_length_map.items():
        if length != best_result[1]:
            # 目前发现返回信息里面的 runTimeMilliseconds 是运行时间相关，可能不一样
            len_delta = best_result[1] - length
            if len_delta >= 5:
                logging.info(
                    f'found stale change id: {change_id}, repo: {repo}, instance: {instance}, len_delta: {len_delta}'
                )
    return best_result


def truncate_files(patch_set):
    if not patch_set or not patch_set.get('files'):
        return False
    if len(patch_set['files']) >= 500:
        patch_set['files'] = patch_set['files'][:500]
        return True
    return False


def wrap_perceval_message(change_data):
    patch_sets = change_data.get('patchSets', [])
    # keep first 3 and last 3 patch sets if more than 6 patch sets
    if len(patch_sets) > 6:
        change_data['patchSets'] = patch_sets[:3] + patch_sets[-3:]
        patch_sets = change_data['patchSets']
        change_data['_patchSetsTruncatedTo6'] = True

    files_truncated = False
    if truncate_files(change_data.get('currentPatchSet')):
        files_truncated = True

    for patch in patch_sets:
        if truncate_files(patch):
            files_truncated = True

    if files_truncated:
        change_data['_filesTruncatedTo500'] = True

    now = datetime.now()
    snapshot_on = now.strftime('%Y-%m-%d')  # like 2024-04-20
    now_in_seconds = time.time()
    change_data['snapshotOn'] = snapshot_on
    last_updated = change_data['lastUpdated']
    return {
        'backend_name': 'Gerrit',
        'backend_version': '0.13.1',
        'category': 'review',
        'classified_fields_filtered': None,
        'data': change_data,
        'origin': 'gerrit.it.chehejia.com',
        'perceval_version': '0.21.1',
        'search_fields': {},
        'tag': 'gerrit.it.chehejia.com',
        'timestamp': now_in_seconds,
        'updated_on': last_updated,
        # 'uuid': '72fe7962a279614336eb4fc83996b676e8b83a5a'
        'uuid': uuid.uuid4().hex,
    }


class MaxMessageException(Exception):
    pass


def send_to_kafka(change_id, data):
    encoded_data = json.dumps(data).encode('utf-8')  # JSON to bytes
    # max message size is 1MB
    max_size = _kafka_producer_config.get('message.max.bytes') - 50 * 1024
    if len(encoded_data) > max_size:
        raise MaxMessageException(
            f'message size {len(encoded_data)} is too large')
    if not _target_topic:
        logging.warning('no target topic specified, skipping send to kafka')
        return

    # Callback to check whether the message was sent successfully or not
    def delivery_callback(err, msg):
        if err:
            logging.error(
                f'change: {change_id}, message delivery failed: {err}')
        else:
            logging.info(
                f'change: {change_id}, message delivered to {msg.topic()} [{msg.partition()}:{msg.offset()}]'
            )

    # Produce and send the message
    _producer.produce(_target_topic, encoded_data, callback=delivery_callback)

    # Wait for any outstanding messages to be delivered
    _producer.flush()


def get_common_where_conditions():
    """
    Returns common WHERE conditions used by both regular refresh and fallback sync queries.
    These conditions handle basic filtering for processable changes.
    """
    return '''
    -- Avoid processing items currently being worked on
    (scrap_task_status is distinct from 'doing')
    -- Respect existing retry logic - wait 60 seconds after failure
    and (last_failed_time is null or last_failed_time < now() - interval '60 seconds')
    -- Don't process deleted changes
    and (event_type is null or event_type not in ('change-deleted'))
    -- Private changes cannot be accessed by our account
    and (private is distinct from true)
    -- Stop processing after 10 consecutive failures
    and (continuous_failed_count is null or continuous_failed_count <= 10)
    -- Don't process changes with permanent failure reasons
    and failed_reason is null
    '''


def get_to_be_refreshed_items():
    common_conditions = get_common_where_conditions()
    sql = f'''
select *
from gerrit_change_task_queue
where (last_scrap_at is null or last_scrap_at < last_event_at)
    -- 目前不需要那么高的时效性，2小时以内的不处理先不刷新
    -- 刷新太快可能碰到HA导致的数据未同步问题
    and last_event_at <= now() - interval '2 hours'
    -- 目前出现过事件后20多分钟去采集数据都不成功的按理
    -- 这里控制下retry的间隔时间，避免短时间内的retry，期望能改善这种情况
    and (scrap_task_updated_at is null or scrap_task_updated_at <= now() - interval '10 minutes')
    -- Common filtering conditions
    and {common_conditions}
order by
    extract(epoch from (last_event_at - last_scrap_at)) desc NULLS LAST
limit 50
'''
    items = execute_sql(sql)
    return items


def get_fallback_sync_candidates():
    """
    Identifies changes that may have missed Kafka events and need fallback processing.

    Returns changes where:
    - Time gap between last_scrap_at and last_event_at is 8-120 hours
    - Change status is 'NEW'
    - Haven't been processed by fallback sync in the last 24 hours
    - Last event occurred within the last 7 days (prevents processing very old changes)
    - Meet all common filtering conditions

    Orders by last_fallback_processed_at (nulls first) then by time gap (desc)
    to prioritize unprocessed changes and those with larger gaps.
    """
    common_conditions = get_common_where_conditions()
    sql = f'''
select *
from gerrit_change_task_queue
where
    -- Fallback-specific time gap criteria (8-120 hours)
    (last_scrap_at - last_event_at) >= interval '8 hours'
    and (last_scrap_at - last_event_at) <= interval '120 hours'
    -- Only process NEW status changes for fallback sync
    and change_status = 'NEW'
    -- Only consider changes with recent activity (within last 7 days)
    and last_event_at >= now() - interval '7 days'
    -- 24-hour cooldown: don't process same change too frequently
    and (last_fallback_processed_at is null or last_fallback_processed_at < now() - interval '24 hours')
    -- Common filtering conditions
    and {common_conditions}
order by
    -- Prioritize changes never processed by fallback sync, then by time gap
    last_fallback_processed_at asc nulls first,
    (last_scrap_at - last_event_at) desc
limit 100
'''
    items = execute_sql(sql)
    return items


def update_items_to_doing(items):
    if not items:
        return
    changes = [(item['change_id'], item['repo']) for item in items]

    conditions = list()
    for change_id, repo in changes:
        conditions.append(f"(change_id = {change_id} AND repo = '{repo}')")
    sql_conditions = ' OR '.join(conditions)
    sql = f'''
    UPDATE gerrit_change_task_queue
    SET scrap_task_status = 'doing', scrap_task_updated_at = now()
        ,scrap_count = coalesce(scrap_count, 0) + 1
    WHERE {sql_conditions}
    '''
    execute_sql(sql, commit=True)


def done_change_id(change_id, done_time, project, status, origin_length):
    '''once succeed, set continuous_failed_count to 0 '''
    sql = '''
UPDATE gerrit_change_task_queue
SET scrap_task_status = 'done'
    ,scrap_task_updated_at = now()
    ,last_scrap_at=%s
    ,change_status=%s
    ,scrap_success_count = coalesce(scrap_success_count, 0) + 1
    ,continuous_failed_count = 0
    ,failed_reason=NULL
    ,stats=jsonb_set(coalesce(stats, '{}'::jsonb), '{origin_length}', '%s')
WHERE change_id = %s and repo = %s
    -- 只有doing的才能被设置为done，这里避免这样的情况:
    -- 一个change的E1来了处理中，然后E2来了，然后处理E1的逻辑完成设置done了导致E2不处理了
    and scrap_task_status = 'doing'
'''
    execute_sql(sql, (done_time, status, origin_length, change_id, project),
                commit=True)


def fail_change_id(change_id, repo, fail_time, failed_reason=None):
    sql = '''
UPDATE gerrit_change_task_queue
SET scrap_task_status = 'failed'
    ,scrap_task_updated_at = now()
    ,continuous_failed_count = coalesce(continuous_failed_count, 0) + 1
    ,last_failed_time = %s
    ,failed_reason = %s
WHERE change_id = %s and repo = %s
    and scrap_task_status = 'doing'
'''
    execute_sql(sql, (fail_time, failed_reason, change_id, repo), commit=True)


def update_fallback_processed_timestamp(change_id, repo):
    """
    Updates the last_fallback_processed_at timestamp for a specific change.

    This function is called BEFORE processing each change in the fallback sync
    to prevent the same change from blocking others during the 24-hour cooldown period.
    The timestamp is updated regardless of whether the subsequent processing succeeds or fails.

    Args:
        change_id (int): The Gerrit change number
        repo (str): The repository name

    Returns:
        bool: True if the update was successful, False otherwise
    """
    sql = '''
UPDATE gerrit_change_task_queue
SET last_fallback_processed_at = now()
WHERE change_id = %s AND repo = %s
'''
    try:
        execute_sql(sql, (change_id, repo), commit=True)
        logging.info(f'Updated fallback processed timestamp for change {change_id} in repo {repo}')
        return True
    except Exception as e:
        logging.error(f'Failed to update fallback processed timestamp for change {change_id} in repo {repo}: {e}')
        return False


async def process_fallback_changes(candidate_changes):
    """
    Processes a list of candidate changes for fallback synchronization.

    For each change:
    1. Updates the last_fallback_processed_at timestamp BEFORE processing
    2. Processes the change using the existing refresh_item() function
    3. Handles individual change errors gracefully without stopping batch processing

    Args:
        candidate_changes (list): List of change dictionaries from get_fallback_sync_candidates()

    Returns:
        dict: Processing statistics including success_count, error_count, and errors list
    """
    if not candidate_changes:
        logging.info('No fallback sync candidates to process')
        return {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }

    logging.info(f'Processing {len(candidate_changes)} fallback sync candidates')

    success_count = 0
    error_count = 0
    errors = []

    for change in candidate_changes:
        change_id = change['change_id']
        repo = change['repo']

        try:
            # Update fallback processed timestamp BEFORE processing
            # This prevents the same change from blocking others during the 24-hour cooldown
            timestamp_updated = update_fallback_processed_timestamp(change_id, repo)
            if not timestamp_updated:
                error_msg = f'Failed to update fallback timestamp for change {change_id} in repo {repo}'
                logging.warning(error_msg)
                errors.append({
                    'change_id': change_id,
                    'repo': repo,
                    'error': error_msg,
                    'stage': 'timestamp_update'
                })
                error_count += 1
                continue

            # Process the change using existing refresh_item logic
            logging.info(f'Fallback processing change {change_id} in repo {repo}')
            await refresh_item(change)

            success_count += 1
            logging.info(f'Successfully processed fallback change {change_id} in repo {repo}')

            # Add delay between fallback items to avoid overwhelming Gerrit server
            await asyncio.sleep(2)

        except Exception as e:
            error_msg = f'Failed to process fallback change {change_id} in repo {repo}: {str(e)}'
            logging.error(error_msg, exc_info=True)
            errors.append({
                'change_id': change_id,
                'repo': repo,
                'error': str(e),
                'stage': 'processing'
            })
            error_count += 1
            # Continue processing other changes despite this error
            continue

    logging.info(f'Fallback processing completed: {success_count} successful, {error_count} errors')

    return {
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }


async def refresh_item(item):
    change_id = item['change_id']
    logging.info(f'begin to refresh change item: {change_id}')
    now = datetime.now()
    change_detail, msg_length = await get_best_gerrit_change_detail(
        change_id, item['repo'])
    if not change_detail:
        fail_change_id(change_id, item['repo'], now)
        return
    perceval_msg = wrap_perceval_message(change_detail)
    try:
        send_to_kafka(change_id, perceval_msg)
    except MaxMessageException as mme:
        logging.error(f'change: {change_id}, failed to send to kafka: {mme}',
                      exc_info=True)
        fail_change_id(change_id, item['repo'], now, failed_reason='too_large')
        return
    done_change_id(
        change_id,
        now,
        change_detail.get('project'),
        change_detail.get('status', ''),
        msg_length,
    )


async def refresh_change_items():
    while True:
        try:
            logging.info('begin to refresh change items')
            items = get_to_be_refreshed_items() or []
            update_items_to_doing(items)
            for item in items:
                try:
                    await refresh_item(item)
                except Exception as e:
                    logging.warning(
                        f'failed to refresh change item: {item["change_id"]}: {e}',
                        exc_info=True)
                    continue
            if len(items) == 0:
                await asyncio.sleep(60)
        except Exception as e:
            logging.error(f'failed to refresh change items: {e}', exc_info=True)
        await asyncio.sleep(10)


async def recycle_zoombies():
    while True:
        try:
            sql = '''
update gerrit_change_task_queue
    set scrap_task_status = '', scrap_task_updated_at = now()
where
    scrap_task_status = 'doing'
    and scrap_task_updated_at <= (now() - interval '30 minutes')
'''
            execute_sql(sql, commit=True)
        except Exception as e:
            logging.error(f'failed to recycle zoombies: {e}', exc_info=True)
        # sleep 30 minutes, execute every 20 minutes
        await asyncio.sleep(60 * 20)


async def fallback_sync_loop():
    """
    Main asyncio task for fallback synchronization that runs every 12 hours.

    This task identifies and re-processes Gerrit changes that may have missed Kafka events,
    specifically targeting NEW status changes where there's a significant time gap
    between the last event and last scraping attempt (8-120 hours).

    The task:
    1. Runs every 12 hours using asyncio.sleep
    2. Identifies candidate changes using get_fallback_sync_candidates()
    3. Processes candidates using process_fallback_changes()
    4. Provides comprehensive logging for monitoring
    5. Handles database connection errors gracefully
    """
    logging.info('Fallback sync loop started - will run every 12 hours')

    while True:
        try:
            logging.info('Starting fallback sync task')

            start_time = datetime.now()

            try:
                candidate_changes = get_fallback_sync_candidates()
                if candidate_changes is None:
                    candidate_changes = []

                candidate_count = len(candidate_changes)
                logging.info(f'Fallback sync identified {candidate_count} candidate changes for processing')

                if candidate_count == 0:
                    logging.info('No changes need fallback processing at this time')
                else:
                    # Process the candidate changes
                    processing_results = await process_fallback_changes(candidate_changes)

                    # Log completion summary with statistics
                    end_time = datetime.now()
                    duration = end_time - start_time

                    success_count = processing_results['success_count']
                    error_count = processing_results['error_count']
                    errors = processing_results['errors']

                    logging.info(f'Fallback sync completed in {duration.total_seconds():.1f} seconds')
                    logging.info(f'Processing summary: {success_count} successful, {error_count} errors out of {candidate_count} candidates')

                    # Log individual errors if any occurred
                    if error_count > 0:
                        logging.warning(f'Fallback sync encountered {error_count} errors:')
                        for error in errors:
                            change_id = error['change_id']
                            repo = error['repo']
                            error_msg = error['error']
                            stage = error['stage']
                            logging.error(f'Change {change_id} in repo {repo} failed at {stage}: {error_msg}')

                    # Log success details
                    if success_count > 0:
                        logging.info(f'Successfully processed {success_count} changes via fallback sync')

            except Exception as e:
                # Handle database connection errors and other issues gracefully
                logging.error(f'Fallback sync task failed during candidate identification or processing: {e}', exc_info=True)
                logging.info('Fallback sync will retry on next scheduled run')

        except Exception as e:
            # Catch-all for any unexpected errors in the main loop
            logging.error(f'Unexpected error in fallback sync loop: {e}', exc_info=True)

        # Sleep for 12 hours before next execution
        logging.info('Fallback sync task completed, sleeping for 12 hours until next run')
        await asyncio.sleep(60 * 60 * 12)  # 12 hours in seconds


def cleanup():
    """清理资源，包括停止线程和关闭Kafka连接"""
    logging.info('Starting cleanup process...')
    # 设置停止标志来终止事件消费线程
    _stop_event_consuming.set()
    _consumer.close()
    logging.info('Cleanup completed')


atexit.register(cleanup)


async def run():
    # item = dict(change_id=1012114, repo='fe/lixiang/rnvic')
    # await refresh_item(item)

    # 启动Kafka事件消费线程
    event_thread = threading.Thread(
        target=event_consuming_loop,
        name='KafkaEventConsumer',
        daemon=True  # 设为守护线程，主程序退出时自动结束
    )
    event_thread.start()
    logging.info('Kafka event consuming thread started')

    # 启动其他异步任务
    task_refresh_worker = asyncio.create_task(refresh_change_items())
    task_recycle = asyncio.create_task(recycle_zoombies())
    task_fallback_sync = asyncio.create_task(fallback_sync_loop())

    try:
        await asyncio.gather(task_refresh_worker, task_recycle, task_fallback_sync)
    except KeyboardInterrupt:
        logging.info('Received interrupt signal, shutting down...')
        # 设置停止标志
        _stop_event_consuming.set()
        # 等待线程正常结束（最多等待5秒）
        event_thread.join(timeout=5)
        if event_thread.is_alive():
            logging.warning('Kafka event consuming thread did not exit cleanly')
        raise


def main():
    asyncio.run(run())


if __name__ == '__main__':
    fire.Fire()
