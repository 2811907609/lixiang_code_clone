"""
Core telemetry data structures and types for the SOP Agents system.

This module defines all the data models, enums, and serialization methods
needed for telemetry collection and storage.
"""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


class TaskStatus(Enum):
    """Status of task execution."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class AgentType(Enum):
    """Type of agent in the system."""
    SUPERVISOR = "supervisor"
    MICRO = "micro"
    TOOL_CALLING = "tool_calling"
    CODE = "code"
    MANAGED = "managed"


@dataclass
class TokenUsage:
    """Token usage statistics for LLM calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_breakdown: Dict[str, "TokenUsage"] = field(default_factory=dict)
    cost_estimate: Optional[float] = None

    def __post_init__(self):
        """Calculate total tokens if not provided."""
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens

    def add_usage(self, other: "TokenUsage") -> None:
        """Add another TokenUsage to this one."""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens

        # Merge model breakdowns
        for model, usage in other.model_breakdown.items():
            if model in self.model_breakdown:
                self.model_breakdown[model].add_usage(usage)
            else:
                self.model_breakdown[model] = usage

        # Add cost estimates if both exist
        if self.cost_estimate is not None and other.cost_estimate is not None:
            self.cost_estimate += other.cost_estimate
        elif other.cost_estimate is not None:
            self.cost_estimate = other.cost_estimate

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model_breakdown": {
                model: usage.to_dict() for model, usage in self.model_breakdown.items()
            },
            "cost_estimate": self.cost_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenUsage":
        """Create TokenUsage from dictionary."""
        model_breakdown = {}
        if "model_breakdown" in data:
            model_breakdown = {
                model: cls.from_dict(usage_data)
                for model, usage_data in data["model_breakdown"].items()
            }

        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            model_breakdown=model_breakdown,
            cost_estimate=data.get("cost_estimate"),
        )


@dataclass
class EnvironmentInfo:
    """Environment context information."""
    os_type: str
    os_version: str
    python_version: str
    working_directory: str
    project_root: str
    user_name: Optional[str] = None
    timezone: str = "UTC"
    environment_variables: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentInfo":
        """Create EnvironmentInfo from dictionary."""
        return cls(**data)


@dataclass
class LLMCall:
    """Information about a single LLM call."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration: float
    timestamp: datetime
    cost_estimate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
            "cost_estimate": self.cost_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMCall":
        """Create LLMCall from dictionary."""
        return cls(
            model=data["model"],
            prompt_tokens=data["prompt_tokens"],
            completion_tokens=data["completion_tokens"],
            total_tokens=data["total_tokens"],
            duration=data["duration"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            cost_estimate=data.get("cost_estimate"),
        )


@dataclass
class CodeMetrics:
    """Metrics about code changes during task execution."""
    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    lines_modified: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeMetrics":
        """Create CodeMetrics from dictionary."""
        return cls(**data)


@dataclass
class ToolExecution:
    """Information about tool execution."""
    tool_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    error_message: Optional[str] = None

    def __post_init__(self):
        """Calculate duration if end_time is provided."""
        if self.end_time and self.duration is None:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tool_name": self.tool_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status.value,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolExecution":
        """Create ToolExecution from dictionary."""
        return cls(
            tool_name=data["tool_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            duration=data.get("duration"),
            status=TaskStatus(data.get("status", TaskStatus.NOT_STARTED.value)),
            error_message=data.get("error_message"),
        )


@dataclass
class AgentExecution:
    """Information about agent execution."""
    agent_type: AgentType
    agent_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    llm_calls: List[LLMCall] = field(default_factory=list)
    tools_used: List[ToolExecution] = field(default_factory=list)
    error_message: Optional[str] = None

    def __post_init__(self):
        """Calculate duration if end_time is provided."""
        if self.end_time and self.duration is None:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def get_total_tokens(self) -> TokenUsage:
        """Calculate total token usage for this agent."""
        total = TokenUsage()
        for llm_call in self.llm_calls:
            call_usage = TokenUsage(
                prompt_tokens=llm_call.prompt_tokens,
                completion_tokens=llm_call.completion_tokens,
                total_tokens=llm_call.total_tokens,
            )
            total.add_usage(call_usage)
        return total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_type": self.agent_type.value,
            "agent_name": self.agent_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status.value,
            "llm_calls": [call.to_dict() for call in self.llm_calls],
            "tools_used": [tool.to_dict() for tool in self.tools_used],
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentExecution":
        """Create AgentExecution from dictionary."""
        return cls(
            agent_type=AgentType(data["agent_type"]),
            agent_name=data["agent_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            duration=data.get("duration"),
            status=TaskStatus(data.get("status", TaskStatus.NOT_STARTED.value)),
            llm_calls=[LLMCall.from_dict(call) for call in data.get("llm_calls", [])],
            tools_used=[ToolExecution.from_dict(tool) for tool in data.get("tools_used", [])],
            error_message=data.get("error_message"),
        )


@dataclass
class TaskExecution:
    """Information about a complete task execution."""
    task_id: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    sop_category: Optional[str] = None
    agents: List[AgentExecution] = field(default_factory=list)
    tools: List[ToolExecution] = field(default_factory=list)
    llm_calls: List[LLMCall] = field(default_factory=list)
    code_changes: CodeMetrics = field(default_factory=CodeMetrics)
    error_message: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate task duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def get_total_tokens(self) -> TokenUsage:
        """Calculate total token usage for this task."""
        total = TokenUsage()

        # Add direct LLM calls
        for llm_call in self.llm_calls:
            call_usage = TokenUsage(
                prompt_tokens=llm_call.prompt_tokens,
                completion_tokens=llm_call.completion_tokens,
                total_tokens=llm_call.total_tokens,
            )
            total.add_usage(call_usage)

        # Add agent LLM calls
        for agent in self.agents:
            agent_usage = agent.get_total_tokens()
            total.add_usage(agent_usage)

        return total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status.value,
            "sop_category": self.sop_category,
            "agents": [agent.to_dict() for agent in self.agents],
            "tools": [tool.to_dict() for tool in self.tools],
            "llm_calls": [call.to_dict() for call in self.llm_calls],
            "code_changes": self.code_changes.to_dict(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskExecution":
        """Create TaskExecution from dictionary."""
        return cls(
            task_id=data["task_id"],
            description=data["description"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            status=TaskStatus(data.get("status", TaskStatus.NOT_STARTED.value)),
            sop_category=data.get("sop_category"),
            agents=[AgentExecution.from_dict(agent) for agent in data.get("agents", [])],
            tools=[ToolExecution.from_dict(tool) for tool in data.get("tools", [])],
            llm_calls=[LLMCall.from_dict(call) for call in data.get("llm_calls", [])],
            code_changes=CodeMetrics.from_dict(data.get("code_changes", {})),
            error_message=data.get("error_message"),
        )


@dataclass
class TelemetrySession:
    """Complete telemetry session containing all collected data."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    environment: EnvironmentInfo = field(default_factory=lambda: EnvironmentInfo("", "", "", "", ""))
    tasks: List[TaskExecution] = field(default_factory=list)
    total_tokens: TokenUsage = field(default_factory=TokenUsage)
    total_duration: float = 0.0

    def add_task(self, task: TaskExecution) -> None:
        """Add a task to this session."""
        self.tasks.append(task)

        # Update total tokens
        task_tokens = task.get_total_tokens()
        self.total_tokens.add_usage(task_tokens)

        # Update total duration
        if task.duration:
            self.total_duration += task.duration

    def get_session_duration(self) -> Optional[float]:
        """Calculate total session duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "session_duration": self.get_session_duration(),
            "environment": self.environment.to_dict(),
            "tasks": [task.to_dict() for task in self.tasks],
            "total_tokens": self.total_tokens.to_dict(),
            "total_duration": self.total_duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetrySession":
        """Create TelemetrySession from dictionary."""
        return cls(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            environment=EnvironmentInfo.from_dict(data.get("environment", {})),
            tasks=[TaskExecution.from_dict(task) for task in data.get("tasks", [])],
            total_tokens=TokenUsage.from_dict(data.get("total_tokens", {})),
            total_duration=data.get("total_duration", 0.0),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "TelemetrySession":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save session data to a JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "TelemetrySession":
        """Load session data from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())


# Utility functions for serialization
def serialize_telemetry_data(data: Union[TelemetrySession, TaskExecution, AgentExecution]) -> str:
    """Serialize any telemetry data structure to JSON."""
    return data.to_json() if hasattr(data, 'to_json') else json.dumps(data.to_dict(), indent=2, default=str)


def deserialize_telemetry_data(json_str: str, data_type: str) -> Union[TelemetrySession, TaskExecution, AgentExecution]:
    """Deserialize JSON string to appropriate telemetry data structure."""
    data = json.loads(json_str)

    if data_type == "session":
        return TelemetrySession.from_dict(data)
    elif data_type == "task":
        return TaskExecution.from_dict(data)
    elif data_type == "agent":
        return AgentExecution.from_dict(data)
    else:
        raise ValueError(f"Unknown data type: {data_type}")
