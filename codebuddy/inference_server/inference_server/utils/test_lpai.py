from .lpai import LpaiUtils

_lpai = None


def get_lpai():
    global _lpai
    if _lpai is not None:
        return _lpai

    lpaiutil = LpaiUtils(ns='sc-ep')
    _lpai = lpaiutil
    return lpaiutil


def test_list_models():
    lpaiutil = get_lpai()
    models = lpaiutil.model.listallmodels()
    print(f'models: {models}')
    versions = lpaiutil.model.get_model_versions(models[0]['model_set_name'])
    print(f'model versions: {versions}')


def test_list_inferences():
    lpaiutil = get_lpai()
    inf = lpaiutil.inference.get('lpai-env-test')
    print(f'inference: {inf}')


def test_update_inferences():
    lpaiutil = get_lpai()
    modelset_name = 'codellama-ep-priv-code-finetuned'
    inf_name = 'lpai-env-test'
    r = lpaiutil.update_inference_to_latest_model(inf_name=inf_name,
                                                  modelset_name=modelset_name)
    print(r)
