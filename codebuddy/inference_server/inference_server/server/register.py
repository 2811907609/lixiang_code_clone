import logging
from typing import List

import requests

from inference_server.config import InstanceConfig
from inference_server.envs import config

logger = logging.getLogger(__name__)

_cluster_register_url_map = {
    'STAGING':
        'https://portal-k8s-staging.ep.chehejia.com/api/copilot/v1/register-model',
    'PROD':
        'https://portal-k8s-prod.ep.chehejia.com/api/copilot/v1/register-model',
}


def register_model(name,
                   service_name,
                   lpai_domain,
                   clusters=None,
                   labels=None,
                   is_default=False):
    url = f'https://{lpai_domain}/inference/sc-ep/{service_name}/'
    data = {
        'name': name,
        'url': url,
        'labels': labels,
        'is_default': is_default,
    }

    for cluster in (clusters or []):
        cluster_url = _cluster_register_url_map.get(cluster.strip().upper())
        if not cluster_url:
            continue
        try:
            # ignore if failed to register
            res = requests.post(cluster_url, json=data)
            logger.info(
                f'register model {name} to {cluster_url}, status: {res.status_code}, text: {res.text}'
            )
        except Exception as e:
            logger.error(f'register model {name} to {cluster_url}, error: {e}')


def register(instance_config: InstanceConfig):
    if instance_config.disable_register:
        logger.info('configured to disable register, skip.......')
        return
    lpai_service_name = config.LPAI_SERVICE_NAME
    if not lpai_service_name:
        logger.warning('you should give a lpai service name to register model')
        return
    exposed_model_names: List[str] = []
    models = instance_config.get('models', {})
    for model_name in models:
        exposed_model_names.append(model_name)
    clusters = instance_config.register_clusters or ['STAGING', 'PROD']

    # labels is something like category=llama;size=7b;inference_by=vllm
    labels = instance_config.model_labels or {}
    for model_name in exposed_model_names:
        if not model_name:
            continue
        register_model(model_name,
                       lpai_service_name,
                       lpai_domain=instance_config.lpai_endpoint,
                       clusters=clusters,
                       labels=labels)
