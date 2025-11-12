'''
codebuddy_fe is the golang service between the model backend
'''
import json

import requests

_default_host = 'https://portal-k8s-staging.ep.chehejia.com'


def get_record_by_completion_id(completion_id, host=None):
    host = host or _default_host
    path = '/api/copilot/record'
    u = host + path
    querystring = {
        'completionID': completion_id,
    }
    response = requests.request("GET", u, params=querystring)
    rows = response.json().get('rows')
    if rows:
        record = rows[0]
        record['prompt'] = json.loads(record['prompt'])
        record['result'] = json.loads(record['result'])
        return record
    else:
        print(f'failed to find record by completion_id {completion_id}')
