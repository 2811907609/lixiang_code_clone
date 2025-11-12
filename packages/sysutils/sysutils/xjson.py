import json
from dataclasses import asdict


# Custom JSON encoder for dataclasses
class DataclassEncoder(json.JSONEncoder):

    def default(self, obj):
        # deal with dataclass
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        # deal with pydantic model
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        return super().default(obj)


def json_dumps(obj, **kwargs):
    return json.dumps(obj, cls=DataclassEncoder, **kwargs)


def json_loads(s, **kwargs):
    return json.loads(s, **kwargs)
