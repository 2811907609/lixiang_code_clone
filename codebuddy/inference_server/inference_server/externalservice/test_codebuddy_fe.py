from commonlibs.encoding import yaml_print
from .codebuddy_fe import get_record_by_completion_id


def test_get_completion_by_id():
    completion_ids = [
        'cmpl-61ddf1ad-53cf-4c06-85fb-019024054aa2',
    ]

    for cid in completion_ids:
        res = get_record_by_completion_id(cid)
        yaml_print(res)
