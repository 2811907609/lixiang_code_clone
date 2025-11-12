from io import StringIO
from pathlib import Path

from commonlibs.encoding import yaml_dump, yaml_load_dir

_parent_dir = Path(__file__).parent


def test_yaml_load_dir():
    test_dir = _parent_dir / 'testdata'
    result = yaml_load_dir(test_dir)
    print('yaml load dir result', result)
    ids = set()
    for doc in result:
        for item in doc:
            ids.add(item['id'])
    assert set(ids) == set([1, 2, 3, 4])


def test_yaml_dump_to_str():
    obj = {'key': '这是value'}
    result = yaml_dump(obj)
    expected_output = 'key: 这是value\n'
    assert result == expected_output


def test_yaml_dump_to_file_handler():
    obj = {'key': '这是value'}
    file_handler = StringIO()
    yaml_dump(obj, file_handler)
    file_handler.seek(0)
    result = file_handler.read()
    expected_output = 'key: 这是value\n'
    assert result == expected_output


def test_yaml_dump_multi_lines():
    obj = {
        'key':
            'line1 with | in it.\n\n  line2 start with tab\nline3 with space at the end '
    }
    result = yaml_dump(obj)
    expected_output = '''\
key: |-
  line1 with | in it.

    line2 start with tab
  line3 with space at the end \n'''
    assert result == expected_output
