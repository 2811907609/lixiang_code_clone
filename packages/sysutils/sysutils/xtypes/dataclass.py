from dataclasses import fields, is_dataclass
from typing import List, Optional, Type, TypeVar, Union, get_args, get_origin

T = TypeVar('T')


def get_optional_wrapped_type(t: Type[Optional[T]]) -> T:
    '''Optional[Tokenizer] -> Tokenizer'''
    outer_type = get_origin(t)
    type_args = get_args(t)
    if outer_type is Union and type(None) in type_args:
        for arg_type in type_args:
            if arg_type is not type(None):
                return arg_type


def get_wrapped_dict_type(t: T) -> T:
    '''Optional[Dict[K, Tokenizer]] -> Tokenizer'''
    d = get_optional_wrapped_type(t)
    # check if is Dict, for Dict, get_origin(T) is dict
    if get_origin(d) is dict:
        # get_args(Dict[K, V]) will get (K, V)
        return get_args(d)[1]


def dataclass_from_dict(data_class: Type[T], data: dict) -> T:
    if not is_dataclass(data_class):
        return data

    fieldtypes = {f.name: f.type for f in fields(data_class)}
    init_values = {}

    for field, field_type in fieldtypes.items():
        value = data.get(field)
        if value is None:
            init_values[field] = None
            continue

        if is_dataclass(field_type):
            init_values[field] = dataclass_from_dict(field_type, data[field])
        elif dict_type := get_wrapped_dict_type(field_type):
            init_values[field] = {
                k: dataclass_from_dict(dict_type, v) for k, v in value.items()
            }
        elif wrapped_type := get_optional_wrapped_type(field_type):
            init_values[field] = dataclass_from_dict(wrapped_type, data[field])
        elif isinstance(field_type, type) and issubclass(field_type, List):
            item_type = get_args(field_type)[0]
            init_values[field] = [
                dataclass_from_dict(item_type, item)
                if is_dataclass(item_type) else item for item in data[field]
            ]
        else:
            init_values[field] = data.get(field)

    return data_class(**init_values)
