# Docker Sandbox

This module provides secure Docker-based sandboxed execution of shell commands for AI agents.

## Features

- 🔒 **Security**: Comprehensive security policies and command validation
- 🐳 **Docker Integration**: Full Docker container management
- 🛠️ **Configurable**: Flexible configuration via YAML files or predefined configs
- 📊 **Resource Control**: Memory, CPU, and network limits
- 🔍 **Monitoring**: Detailed logging and execution tracking

## Quick Start

```python
from ai_agents.tools.sandbox import DockerSandbox

# Initialize sandbox with configuration
sandbox = DockerSandbox(
    session_id="my_sandbox",
    predefined_config="python",
    allow_network=True
)

# Get tools for AI agent
tools = sandbox.tools()
execute_command = tools[0]  # Only one tool: execute_command

# Use the tool
result = execute_command("python --version")
print(result)

# Clean up
sandbox.stop()
```

## Design Principles

The `DockerSandbox` class is specifically designed for AI agents with these principles:

### 🎯 Simple Tool Method

Only one method with simple, unambiguous parameters:

```python
execute_command(command: str) -> str
```

### 🔧 Configuration at Initialization

All complex configuration happens during object creation:

```python
# Configure once during initialization
sandbox = DockerSandbox(
    session_id="ai_session",
    predefined_config="python",        # Environment setup
    memory_limit="1g",                 # Resource limits
    allow_network=True,                # Network access
    security_policy="development",     # Security settings
    mount_volumes={"./code": "/workspace"},  # Volume mounts
    environment_vars={"DEBUG": "1"}    # Environment variables
)

# Then use simple tool
tools = sandbox.tools()
execute_command = tools[0]
result = execute_command("python script.py")  # Simple!
```

### 🛡️ Built-in Safety

- **Automatic security validation** for all commands
- **Resource limits** enforced at container level
- **Network isolation** by default
- **Automatic cleanup** on object destruction

## Configuration Options

### Predefined Configurations

```python
# Available predefined configs:
configs = ["ubuntu", "python", "node", "alpine"]

sandbox = DockerSandbox(
    session_id="my_session",
    predefined_config="python"
)
```

### YAML Configuration

```yaml
# config.yaml
image: "python:3.11-slim"
timeout_seconds: 120.0
memory_limit: "1g"
cpu_limit: "2.0"
network_mode: "bridge"
volumes:
  "./code": "/workspace/code"
environment:
  PYTHONPATH: "/workspace"
  DEBUG: "1"
```

```python
sandbox = DockerSandbox(
    session_id="my_session",
    config_file="config.yaml"
)
```

## Security Policies

Available policies:
- **strict**: Maximum security, blocks dangerous commands
- **development**: Allows package installation, network access
- **permissive**: Allows most commands (use with caution)
- **readonly**: Blocks file modifications

```python
sandbox = DockerSandbox(
    session_id="my_session",
    predefined_config="python",
    security_policy="development"
)
```
