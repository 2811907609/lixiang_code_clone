# Execution Environment Tools

This module provides a unified interface for different execution environments used by AI agents.

## Architecture

```
ExecutionEnvironment (Abstract Base Class)
├── SandboxEnvironment (Sandbox Abstract Base Class)
│   └── DockerSandbox (Docker-based sandbox)
└── HostExecutor (Direct host execution)
```

## Unified Interface

All execution environments implement the same interface:

```python
class ExecutionEnvironment(ABC):
    def tools(self) -> List[Any]:
        """Get tools for AI agents"""

    def start(self) -> None:
        """Start the execution environment"""

    def stop(self) -> None:
        """Stop and clean up the environment"""

    @property
    def is_started(self) -> bool:
        """Check if environment is ready"""
```

## Usage

### Factory Function (Recommended)

```python
from ai_agents.tools.execution import create_execution_environment

# Docker sandbox
docker_env = create_execution_environment(
    "docker",
    session_id="test",
    predefined_config="python"
)

# Host environment
host_env = create_execution_environment("host")

# Both have the same interface
tools = docker_env.tools()  # or host_env.tools()
execute_command = tools[0]
result = execute_command("python --version")

# Clean up
docker_env.stop()
host_env.stop()
```

### Direct Usage

```python
from ai_agents.tools.execution import DockerSandbox, HostExecutor

# Docker sandbox
docker_env = DockerSandbox(
    session_id="my_session",
    predefined_config="python",
    allow_network=True
)

# Host executor
host_env = HostExecutor(
    working_directory="/tmp",
    allow_dangerous_commands=False
)

# Same interface for both
tools = docker_env.tools()
execute_command = tools[0]
result = execute_command("echo 'Hello World!'")
```

## Available Environments

### 1. HostExecutor
- **Type**: `"host"`
- **Description**: Executes commands directly on the host system
- **Use Case**: When you need direct access to the host environment
- **Security**: Basic command validation, no isolation

### 2. DockerSandbox
- **Type**: `"docker"`
- **Description**: Executes commands in isolated Docker containers
- **Use Case**: When you need secure, isolated execution
- **Security**: Full container isolation, comprehensive security policies

## Future Extensions

The architecture is designed to easily support additional execution environments:

- **VM Sandbox**: Virtual machine-based isolation
- **WASM Sandbox**: WebAssembly-based execution
- **Remote Executor**: Execute commands on remote systems

## Benefits

1. **Unified Interface**: All environments use the same `tools()` method
2. **Easy Switching**: Change environment type with one parameter
3. **Extensible**: Add new environments by implementing base classes
4. **Type Safe**: Factory function ensures correct instantiation
5. **Consistent**: Same tool interface regardless of underlying technology
