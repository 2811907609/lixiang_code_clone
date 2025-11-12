
## repoutils
utils for repo(like gerrit, gitlab, gitlabEE, git).


### test and coverage
1. simply run `pytest` to run the tests

```
uv run coverage run -m pytest -vv  -s tests

# you can use -k to filter the tests
uv run coverage run -m pytest -vv  -s -k test_xxx tests
```

2. run `pytest` with coverage
```
uv run coverage  run --source=.  -m pytest -vv  -s -k test_ tests
DEBUG    asyncio:selector_events.py:54 Using selector: KqueueSelector
PASSED
------------------------------------------------------------------------------------ live log teardown -------------------------------------------------------------------------------------
DEBUG    asyncio:selector_events.py:54 Using selector: KqueueSelector

tests/test_xcollections.py::test_list_sliding PASSED
tests/test_xdatetime.py::test_get_current_date PASSED
tests/test_xdatetime.py::test_get_current_datetime PASSED
tests/test_xfs.py::test_count_files 1077
PASSED
tests/test_xhttp.py::test_post_json PASSED
tests/test_xhttp.py::test_post_json_with_custom_headers PASSED
tests/test_xhttp.py::test_post_json_error_response PASSED
tests/test_xhttp.py::test_http_response_methods PASSED
tests/test_xtypes.py::test_renewable_class PASSED

==================================================================================== 13 passed in 0.52s ====================================================================================
```

3. generate coverage report

```
uv run coverage report -m
Name                                 Stmts   Miss  Cover   Missing
------------------------------------------------------------------
sysutils/heartbeat.py                   28      0   100%
sysutils/sidecars/__init__.py            2      0   100%
sysutils/sidecars/autoexit.py           48     31    35%   32-37, 40-47, 50-51, 54-73, 77-79
sysutils/xcollections/__init__.py        3      0   100%
sysutils/xcollections/generator.py       9      8    11%   3-10
sysutils/xcollections/list.py            2      0   100%
sysutils/xdatetime.py                    9      0   100%
sysutils/xfs.py                         23     14    39%   5-25, 33
sysutils/xhttp.py                       34      2    94%   43-44
sysutils/xjson.py                       13      5    62%   10-15
sysutils/xtypes/__init__.py              3      0   100%
sysutils/xtypes/classutils.py           14      1    93%   22
sysutils/xtypes/dataclass.py            35     29    17%   9-14, 19-23, 27-56
tests/test_autoexit.py                  20     12    40%   14-26, 30
tests/test_heartbeat.py                 48      4    92%   10, 13, 66, 69
tests/test_xcollections.py              14      0   100%
tests/test_xdatetime.py                 13      0   100%
tests/test_xfs.py                        7      0   100%
tests/test_xhttp.py                     47      0   100%
tests/test_xtypes.py                    19      0   100%
------------------------------------------------------------------
TOTAL                                  391    106    73%
```
