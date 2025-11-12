from rag_ingest.ingest import ingest_repos


async def test_ingest_repos():
    repo_list = [
        'gerrit.it.chehejia.com:29418/ep/ops/ep_exporter',
        'git@gitlab.chehejia.com:ep/portal/public-constants.git',
    ]
    ssh_key = '/Users/zhangxudong/.ssh/key_for_spapi0001/spapi0001'
    username = 'spapi0001'
    await ingest_repos(repo_list, ssh_key_filepath=ssh_key, username=username)
