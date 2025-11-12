from typing import Dict

from inference_server.backend.basemodel import BaseModel
from inference_server.utils.ipython import is_in_ipython
from inference_server.utils import getLogger

logger = getLogger(__name__)

# key is model type, value is class
_model_cls_map: Dict[str, BaseModel] = {}

# key is class name, value is class
_clsname_cls_map: Dict[str, BaseModel] = {}


def register(*names: tuple[str, ...]):

    def f(cls: BaseModel):
        logger.info(f'model {cls.__name__} registered')
        for n in names:
            # for ipython, autoreload will lead to re-register same model type
            # just ignore it, for prod env, we should raise error
            if not is_in_ipython():
                if n in _model_cls_map:
                    raise ValueError(f'model type {n} registered')
            _model_cls_map[n] = cls
            _clsname_cls_map[cls.__name__] = cls
        return cls

    return f


def get_class_by_model_type(model_type: str) -> BaseModel:
    return _model_cls_map.get(model_type)


def get_class_by_name(clsname: str) -> BaseModel:
    return _clsname_cls_map.get(clsname)
