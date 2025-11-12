"""
SOP Agents Telemetry System

Provides comprehensive monitoring and statistics collection for the three-layer
architecture (CLI Interface → Supervisor Agent → Micro Agents + Tools + SOP).
"""

from .types import (
    TaskStatus,
    AgentType,
    TelemetrySession,
    TaskExecution,
    TokenUsage,
    EnvironmentInfo,
    AgentExecution,
    ToolExecution,
    LLMCall,
    CodeMetrics,
    serialize_telemetry_data,
    deserialize_telemetry_data,
)

from .data_store import TelemetryDataStore
from .collector import TelemetryCollector
from .manager import TelemetryManager
from .instrumentation import (
    TelemetryInstrumentedAgent,
    telemetry_context,
    TelemetryContext,
)
from .error_handler import (
    TelemetryErrorHandler,
    get_error_handler,
    safe_telemetry_operation,
    safe_telemetry_call,
    safe_storage_operation,
    safe_instrumentation,
    with_fallback_data,
    log_telemetry_error,
    ensure_safe_json_serialization,
    create_fallback_session,
)

__all__ = [
    # Enums
    "TaskStatus",
    "AgentType",

    # Data structures
    "TelemetrySession",
    "TaskExecution",
    "TokenUsage",
    "EnvironmentInfo",
    "AgentExecution",
    "ToolExecution",
    "LLMCall",
    "CodeMetrics",

    # Storage
    "TelemetryDataStore",

    # Collection
    "TelemetryCollector",

    # Management
    "TelemetryManager",

    # Instrumentation
    "TelemetryInstrumentedAgent",
    "telemetry_context",
    "TelemetryContext",

    # Error Handling
    "TelemetryErrorHandler",
    "get_error_handler",
    "safe_telemetry_operation",
    "safe_telemetry_call",
    "safe_storage_operation",
    "safe_instrumentation",
    "with_fallback_data",
    "log_telemetry_error",
    "ensure_safe_json_serialization",
    "create_fallback_session",

    # Utility functions
    "serialize_telemetry_data",
    "deserialize_telemetry_data",
]
