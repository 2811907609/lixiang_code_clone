import os
import time

import requests


class LpaiBase:
    resourcename = ''

    def __init__(self, endpoint=None, ns=None, token=None, **kwargs):
        self.endpoint = endpoint or 'https://lpai.lixiang.com'
        self.ns = ns
        if not token:
            token = os.getenv('LPAI_TOKEN')
            if not token:
                raise ValueError('Token is required')
        self.token = token

    def _get_url(self, ns='', path=None):
        if path:
            return f'{self.endpoint}{path}'
        ns = ns or self.ns
        u = f'{self.endpoint}/lpai/api/{self.resourcename}/v1/namespaces/{ns}'
        return u

    def _headers(self):
        token = f'LpaiJwt {self.token}'
        return {
            'Content-Type': 'application/json',
            'Authorization': token,
        }

    def _request(self,
                 method,
                 url,
                 params=None,
                 data=None,
                 json=None,
                 headers=None,
                 **kwargs):
        print(f'request url: {url}')
        fix_headers = self._headers()
        if headers:
            fix_headers.update(headers)
        res = requests.request(method,
                               url,
                               params=params,
                               data=data,
                               json=json,
                               headers=fix_headers,
                               **kwargs)
        if not res.ok:
            print(f'{res.status_code} {res.text}')
        else:
            jsonres = res.json()
            return jsonres.get('result')


class LpaiModel(LpaiBase):

    def listallmodels(self, ns=None):
        ns = ns or self.ns
        path = f'/lpai/api/model/modelsets/namespaces/{ns}'
        url = self._get_url(path=path)
        params = {
            'page': 1,
            'limit': 1000,
        }
        res = self._request('GET', url, params=params)
        return res.get('data', [])

    def get_by_name(self, name, ns=None):
        ns = ns or self.ns
        allmodels = self.listallmodels(ns=ns)
        for model in allmodels:
            if model['model_set_name'] == name:
                return model
        return None

    def get_model_versions_by_id(self, model_id, ns=None):
        path = f'/lpai/api/model/modelsets/namespaces/{ns}/{model_id}/versions'
        url = self._get_url(path=path)
        res = self._request('GET', url)
        return res or []

    def get_model_versions(self, name, ns=None):
        ns = ns or self.ns
        model = self.get_by_name(name, ns=ns)
        if not model:
            return []
        modelid = model.get('model_set_id')
        return self.get_model_versions_by_id(modelid, ns=ns)

    def get_latest_version(self, name, ns=None):
        versions = self.get_model_versions(name, ns=ns)
        if not versions:
            return None
        return versions[0]


class LpaiVolume(LpaiBase):
    pass


class LpaiInference(LpaiBase):
    resourcename = 'inferences'

    def get(self, name, ns=None):
        ''' get by inference name '''
        url = self._get_url(ns) + f'/inferences/{name}'
        return self._request('GET', url)

    def stop(self, name, ns=None):
        url = self._get_url(ns) + f'/inferences/{name}/stop'
        return self._request('POST', url)

    def start(self, name, ns=None):
        url = self._get_url(ns) + f'/inferences/{name}/start'
        return self._request('POST', url)

    def restart_immediately(self, name, ns=None):
        ''' 这里使用stop then start 而不是restart是因为restart似乎有些更新不起作用
restart看起来只是pod的重启'''
        self.stop(name, ns)
        time.sleep(1)
        self.start(name, ns)

    def _restart(self, name, ns=None):
        url = self._get_url(ns) + f'/inferences/{name}/restart'
        return self._request('POST', url)

    def restart(self, name, ns=None):
        # LPAI 平台那边如果inf没有变化就不会去做restart的动作
        # 因为我们更新一下环境变量来主动触发强制的更新
        extra_env = {
            'EP_STARTED_AT': str(time.time()),
        }
        self.update(name, ns=ns, extra_env=extra_env, restart=True)

    def update(self, name, ns=None, params=None, extra_env=None, restart=False):
        existed = self.get(name, ns)
        if not existed:
            print(f'inference {name} not found')
            return

        resourceid = existed['id']
        if params:
            existed.update(params)

        if not existed.get('env_config'):
            existed['env_config'] = {}

        if extra_env:
            existed['env_config'].update(extra_env)

        url = self._get_url(ns) + f'/inferences/{resourceid}'
        res = self._request('PUT', url, json=existed)
        if restart:
            print(f'will restart {name}')
            time.sleep(3)
            self._restart(name, ns)
        return res


class Lpai:

    def __init__(self, endpoint=None, ns=None, token=None, **kwargs):
        self.inference = LpaiInference(endpoint=endpoint,
                                       ns=ns,
                                       token=token,
                                       **kwargs)
        self.volume = LpaiVolume(endpoint=endpoint,
                                 ns=ns,
                                 token=token,
                                 **kwargs)
        self.model = LpaiModel(endpoint=endpoint, ns=ns, token=token, **kwargs)


class LpaiUtils(Lpai):

    def update_inference_to_latest_model(self,
                                         ns=None,
                                         inf_name='',
                                         modelset_name='',
                                         restart=False):
        inf = self.inference.get(inf_name, ns=ns)
        if not inf:
            print(f'inference {inf_name} not found')
            return
        print(f'inference {inf}')
        modelset = self.model.get_by_name(modelset_name, ns=ns)
        if not modelset:
            print(f'modelset {modelset_name} not found')
            return
        version = self.model.get_latest_version(modelset_name, ns=ns)
        if not version:
            print(f'latest model version {modelset_name} not found')
            return
        print('latest model version', version)

        env_value = f'/lpai/inputs/models/{modelset_name}-{version["model_version"]}'
        modelversion = version['model_version']
        model = {
            'model_set_id': modelset['model_set_id'],
            'model_set': modelset_name,
            'model_version_id': version['model_id'],
            'model_version': modelversion,
            'model_files': '',
            'env_key': 'LPAI_INPUT_MODEL_0',
            'env_value': env_value,
            'model_delete': False,
        }
        # 这里是专门给codellama ep配置的，后续需要挪到别的地方
        trans_modelpath = f'/lpai/inputs/models/{modelset_name}-{modelversion}/CodeLlama-7b-Instruct-hf.fullft'
        modelpath = f'/lpai/inputs/models/{modelset_name}-{modelversion}/CodeLlama-7b-Instruct-hf.fullft.ct2'
        env_config = {
            'LPAI_SERVICE_NAME': 'ct2-codellama7b-ep',
            'MODELPATH': modelpath,
            'MODELTYPE': 'ct2_codellama',
            'TRANSFORMER_MODELPATH': trans_modelpath,
            'EP_LABELS': 'category=codellama;size=7B;inference_by=ct2',
            'EP_STARTED_AT': str(time.time()),
        }
        params = {
            'models': [model],
            'env_config': env_config,
        }
        return self.inference.update(inf_name,
                                     ns=ns,
                                     params=params,
                                     restart=restart)


if __name__ == '__main__':
    import fire
    fire.Fire(LpaiUtils())
