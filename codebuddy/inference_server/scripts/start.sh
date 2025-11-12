#!/bin/bash

export LD_LIBRARY_PATH="/usr/local/cuda/compat"

export UV_PROJECT_ENVIRONMENT="/lpai/venvs/vllm"
export VIRTUAL_ENV="/lpai/venvs/vllm"

this_script_dir=$(dirname "$0")

ENV_FILE="$this_script_dir/.env"

python_script="${this_script_dir}/../main.py"
echo "pwd is: " $(pwd), "script is" $python_script

# Function to start the Python script
start_server() {
    echo "Starting Python script..."

  if [ -f "$ENV_FILE" ]; then
      echo "Loading environment from $ENV_FILE..."
      source "$ENV_FILE"
  else
      echo "No env file found at $ENV_FILE, using current environment."
  fi

    uv run --no-dev ${python_script}
}

start_server

# Restart the Python script when it exits
while true; do
    echo "Python script exited. Restarting..."
    sleep 5
    start_server
done
