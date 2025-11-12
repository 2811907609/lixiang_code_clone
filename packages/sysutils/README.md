
## sysutils
utils for system packages

### test and coverage
1. simply run `pytest` to run the tests

```
uv run pytest -vv  -s -k test_repo_clone  tests
```

2. run `pytest` with coverage
```
uv run coverage  run --source=.  -m pytest -vv  -s -k test_repo_clone  tests
