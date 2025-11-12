

## inference_server
Code for inference services, tests and benchmarks.


### dev
This project use uv to management dependencies and project configs.
Use `uv sync` to install it as an editable package.

```bash
uv venv /lpai/venvs/vllm
export UV_PROJECT_ENVIRONMENT=/lpai/venvs/vllm/
uv sync --inexact  # install dependencies and keep installed packages in environment

PORT=9000 CONFIG_PATH=conf/test.json INSTANCE_NAME=test.opt125m-spec uv run main.py
```

如果你想使用其他模型，参考 conf/test.json 里面的修改即可。

code completion query:

```bash

curl --request POST \
  --url http://localhost:9000/v1/completions \
  --header 'Content-Type: application/json' \
  --data '{
   "language": "python",
   "stop": ["\n\n\n"],
   "n": 1,
   "max_tokens": 40,
   "segments": {
        "prefix": "def fib",
        "suffix": "\n"
    }
}'

```

chat query:

```bash
curl --request POST   --url http://localhost:9000/v1/chat/completions   --header 'Content-Type: application/json'    --data '{
        "messages": [
                {"role": "system", "content": "you are a coding assistant"},
                {"role": "user", "content": "def quicksort(arr):"}
  ], "max_tokens": 20 }'

```

vllm raw query:

```bash
 curl --request POST   --url http://localhost:9000/vllm/v1/chat/completions   --header 'Content-Type: application/json'   --data '{
        "messages": [
                {"role": "system", "content": "you are a coding assistant"},
                {"role": "user", "content": "def quicksort(arr):"}
  ], "max_tokens": 20, "model": "default" }'
```

#### upgrade vllm version
You can use uv to upgrade vllm version of the virtual env by following commands.

```bash
export VIRTUAL_ENV=/lpai/venvs/vllm/
uv pip install vllm==0.7.1
```

### start a model
You can add an instance under `conf/test.json` or use any one in it.

    $ CONFIG_PATH=conf/test.json INSTANCE_NAME="test.opt125m" uv run main.py
