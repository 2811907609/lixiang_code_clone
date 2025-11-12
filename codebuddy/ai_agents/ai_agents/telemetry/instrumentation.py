"""
Unified telemetry instrumentation for all agent types.

This module provides a consistent wrapper-based approach for instrumenting
agents with telemetry collection, supporting both supervisor and micro agents
with automatic context tracking and error isolation.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from smolagents.models import Model, LiteLLMModel

from ai_agents.lib.smolagents.models import LiteLLMModelV2
from .manager import TelemetryManager
from .types import TaskStatus, AgentType, LLMCall
from ai_agents.lib.tracing import get_current_task_id, get_current_agent_id


logger = logging.getLogger(__name__)


class AgentInstrumentor:
    """
    Instrumentor for adding telemetry to agent model calls.

    This class provides functionality to instrument smolagents Model classes
    and other agent frameworks with automatic telemetry collection.
    """

    def __init__(self, collector, error_handler):
        """
        Initialize the agent instrumentor.

        Args:
            collector: TelemetryCollector instance
            error_handler: TelemetryErrorHandler instance
        """
        self.collector = collector
        self.error_handler = error_handler
        self._instrumented_classes = []
        self._original_methods = {}

    def instrument_model_calls(self, model_class):
        """
        Instrument a model class to collect telemetry on generate calls.

        Args:
            model_class: The model class to instrument

        Returns:
            The instrumented model class
        """
        if model_class in self._instrumented_classes:
            logger.debug(f"Model class {model_class.__name__} already instrumented")
            return model_class

        try:
            # Store original methods with a flat structure for compatibility
            class_name = model_class.__name__

            # Instrument generate method if it exists
            if hasattr(model_class, 'generate'):
                original_generate = model_class.generate
                method_key = f"{class_name}.generate"
                self._original_methods[method_key] = (model_class, 'generate', original_generate)
                model_class.generate = self._wrap_generate_method(original_generate, class_name)

            # Instrument generate_stream method if it exists
            if hasattr(model_class, 'generate_stream'):
                original_generate_stream = model_class.generate_stream
                method_key = f"{class_name}.generate_stream"
                self._original_methods[method_key] = (model_class, 'generate_stream', original_generate_stream)
                model_class.generate_stream = self._wrap_generate_stream_method(original_generate_stream, class_name)

            self._instrumented_classes.append(model_class)
            logger.debug(f"Successfully instrumented model class: {class_name}")

        except Exception as e:
            self.error_handler.handle_instrumentation_error(f"Failed to instrument {model_class.__name__}: {e}")

        return model_class
    def _wrap_generate_method(self, original_method, model_name):
        """Create a wrapped version of the generate method."""
        instrumentor = self  # Capture the instrumentor instance

        def wrapped_generate(model_self, *args, **kwargs):
            # Get the actual model ID from the instance if available
            actual_model_name = getattr(model_self, 'model_id', model_name)
            start_time = time.time()
            try:
                result = original_method(model_self, *args, **kwargs)
                duration = time.time() - start_time

                # Record the LLM call
                instrumentor._record_llm_call(actual_model_name, duration, result)

                return result
            except Exception as e:
                duration = time.time() - start_time
                instrumentor._record_llm_call(actual_model_name, duration, None, error=str(e))
                raise

        return wrapped_generate

    def _wrap_generate_stream_method(self, original_method, model_name):
        """Create a wrapped version of the generate_stream method."""
        instrumentor = self  # Capture the instrumentor instance

        def wrapped_generate_stream(model_self, *args, **kwargs):
            # Get the actual model ID from the instance if available
            actual_model_name = getattr(model_self, 'model_id', model_name)
            start_time = time.time()

            try:
                # Get the generator from the original method
                generator = original_method(model_self, *args, **kwargs)

                # Wrap the generator to collect tokens as we iterate
                def token_collecting_generator():
                    total_input_tokens = 0
                    total_output_tokens = 0

                    try:
                        for chunk in generator:
                            # Accumulate token counts from each chunk
                            if hasattr(chunk, 'token_usage'):
                                usage = chunk.token_usage
                                if hasattr(usage, 'input_tokens'):
                                    total_input_tokens += getattr(usage, 'input_tokens', 0)
                                if hasattr(usage, 'output_tokens'):
                                    total_output_tokens += getattr(usage, 'output_tokens', 0)

                            yield chunk

                        # Record telemetry after stream completes
                        duration = time.time() - start_time

                        # Create a mock result object with accumulated tokens
                        class MockStreamResult:
                            def __init__(self):
                                self.token_usage = MockTokenUsage()

                        class MockTokenUsage:
                            def __init__(self):
                                self.input_tokens = total_input_tokens
                                self.output_tokens = total_output_tokens

                        mock_result = MockStreamResult()
                        instrumentor._record_llm_call(actual_model_name, duration, mock_result, is_stream=True)

                    except Exception as e:
                        duration = time.time() - start_time
                        instrumentor._record_llm_call(actual_model_name, duration, None, error=str(e), is_stream=True)
                        raise

                return token_collecting_generator()

            except Exception as e:
                duration = time.time() - start_time
                instrumentor._record_llm_call(actual_model_name, duration, None, error=str(e), is_stream=True)
                raise

        return wrapped_generate_stream

    def _record_llm_call(self, model_name, duration, result=None, error=None, is_stream=False):
        """Record an LLM call with the telemetry collector."""
        try:
            # Get current context
            task_id = get_current_task_id()
            agent_id = get_current_agent_id()

            # Extract token information from result if available
            prompt_tokens = 0
            completion_tokens = 0

            if result:
                # Try different token usage attribute names
                usage = None
                if hasattr(result, 'usage'):
                    usage = result.usage
                elif hasattr(result, 'token_usage'):
                    usage = result.token_usage

                if usage:
                    # Try different token attribute names
                    prompt_tokens_raw = (getattr(usage, 'prompt_tokens', 0) or
                                       getattr(usage, 'input_tokens', 0))
                    completion_tokens_raw = (getattr(usage, 'completion_tokens', 0) or
                                           getattr(usage, 'output_tokens', 0))

                    # Handle Mock objects in tests
                    try:
                        prompt_tokens = int(prompt_tokens_raw) if prompt_tokens_raw else 0
                    except (TypeError, ValueError):
                        prompt_tokens = 0

                    try:
                        completion_tokens = int(completion_tokens_raw) if completion_tokens_raw else 0
                    except (TypeError, ValueError):
                        completion_tokens = 0

            # Create LLMCall object
            llm_call = LLMCall(
                model=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                duration=duration,
                timestamp=datetime.now(timezone.utc),
                cost_estimate=None
            )

            # Record the call
            self.collector.record_llm_call(
                llm_call,
                task_id=task_id,
                agent_id=agent_id
            )

        except Exception as e:
            self.error_handler.handle_instrumentation_error(f"Failed to record LLM call: {e}")

    def uninstrument_all(self):
        """Remove instrumentation from all previously instrumented classes."""
        for model_class in list(self._instrumented_classes):
            try:
                class_name = model_class.__name__

                # Restore original methods using the flat structure
                for method_key, (stored_class, method_name, original_method) in list(self._original_methods.items()):
                    if stored_class == model_class:
                        setattr(model_class, method_name, original_method)
                        del self._original_methods[method_key]

                if model_class in self._instrumented_classes:
                    self._instrumented_classes.remove(model_class)
                logger.debug(f"Uninstrumented model class: {class_name}")

            except Exception as e:
                self.error_handler.handle_instrumentation_error(f"Failed to uninstrument {model_class.__name__}: {e}")

        # Clear any remaining entries
        self._original_methods.clear()


def instrument_smolagents_models(collector, error_handler) -> AgentInstrumentor:
    """
    Instrument smolagents model classes for telemetry collection.

    Args:
        collector: TelemetryCollector instance
        error_handler: TelemetryErrorHandler instance

    Returns:
        AgentInstrumentor instance
    """
    instrumentor = AgentInstrumentor(collector, error_handler)

    try:
        instrumentor.instrument_model_calls(Model)

        instrumentor.instrument_model_calls(LiteLLMModel)

        # Try to instrument custom models
        instrumentor.instrument_model_calls(LiteLLMModelV2)

    except Exception as e:
        error_handler.handle_instrumentation_error(f"Failed to instrument smolagents models: {e}")

    return instrumentor


class TelemetryInstrumentedAgent:
    """
    Universal telemetry wrapper for all agent types.

    This wrapper instruments agent methods to automatically collect telemetry data
    including execution times, tool usage, and integration with hierarchical tracking.
    Supports both supervisor and micro agents with appropriate telemetry patterns.
    """

    def __init__(
        self,
        agent,
        agent_name: str = None,
        agent_type: AgentType = None,
        telemetry_collector=None,
        micro_agent_name: str = None  # Backward compatibility
    ):
        """
        Initialize the telemetry wrapper.

        Args:
            agent: The original agent instance to wrap
            agent_name: Name of the agent for telemetry tracking
            agent_type: Type of agent (SUPERVISOR or MICRO)
            telemetry_collector: Optional TelemetryCollector instance
            micro_agent_name: Backward compatibility parameter for agent name
        """
        self._agent = agent
        # Handle backward compatibility
        self._agent_name = agent_name or micro_agent_name or "unknown_agent"
        self._micro_agent_name = micro_agent_name or agent_name or "unknown_agent"  # Backward compatibility
        self._agent_type = agent_type or AgentType.MICRO
        self._telemetry_collector = telemetry_collector
        self._logger = logging.getLogger(__name__)

        # Proxy all attributes to the original agent (except methods we override)
        excluded_attrs = {'run', '__call__'}
        for attr in dir(agent):
            if (not attr.startswith('_') and
                attr not in excluded_attrs and
                hasattr(agent, attr) and
                not callable(getattr(agent, attr, None))):
                setattr(self, attr, getattr(agent, attr))

    def run(self, task: str, *args, **kwargs):
        """
        Run the agent with telemetry tracking.

        Args:
            task: Task description
            *args, **kwargs: Arguments passed to the original agent

        Returns:
            Task execution result
        """
        return self._execute_with_telemetry('run', task, *args, **kwargs)

    def __call__(self, task: str, **kwargs):
        """
        Call the agent with telemetry tracking (smolagents framework method).

        Args:
            task: Task description
            **kwargs: Arguments passed to the original agent

        Returns:
            Task execution result
        """
        return self._execute_with_telemetry('__call__', task, **kwargs)

    def _execute_with_telemetry(self, method_name: str, task: str, *args, **kwargs):
        """
        Execute agent method with comprehensive telemetry tracking.

        Args:
            method_name: Name of the method being called ('run' or '__call__')
            task: Task description
            *args, **kwargs: Arguments passed to the original agent

        Returns:
            Task execution result
        """
        if not self._telemetry_collector:
            # Fallback to original agent if telemetry is not available
            method = getattr(self._agent, method_name)
            return method(task, *args, **kwargs)

        # Generate unique agent execution ID
        agent_execution_id = f"{self._agent_type.value}_{self._agent_name}_{uuid.uuid4().hex[:8]}"

        # Get current task context for hierarchical tracking
        current_task_id = get_current_task_id()

        start_time = time.time()

        try:
            # Start agent execution tracking
            self._telemetry_collector.start_agent_execution(
                agent_id=agent_execution_id,
                agent_type=self._agent_type,
                agent_name=self._agent_name,
                task_id=current_task_id
            )

            self._logger.debug(
                f"Started telemetry tracking for {self._agent_type.value} agent: "
                f"{self._agent_name} (ID: {agent_execution_id})"
            )

            # Execute the original method
            method = getattr(self._agent, method_name)
            result = method(task, *args, **kwargs)

            # Calculate execution time
            duration = time.time() - start_time

            # End agent execution tracking with success
            self._telemetry_collector.end_agent_execution(
                agent_id=agent_execution_id,
                status=TaskStatus.COMPLETED,
                task_id=current_task_id
            )

            self._logger.debug(
                f"Completed telemetry tracking for {self._agent_type.value} agent: "
                f"{self._agent_name} (duration: {duration:.3f}s)"
            )

            return result

        except Exception as e:
            # Calculate execution time for failed execution
            duration = time.time() - start_time

            # End agent execution tracking with failure
            try:
                self._telemetry_collector.end_agent_execution(
                    agent_id=agent_execution_id,
                    status=TaskStatus.FAILED,
                    task_id=current_task_id,
                    error_message=str(e)
                )

                self._logger.debug(
                    f"Failed telemetry tracking for {self._agent_type.value} agent: "
                    f"{self._agent_name} (duration: {duration:.3f}s, error: {str(e)})"
                )
            except Exception as telemetry_error:
                # Telemetry errors should not mask the original error
                self._logger.warning(f"Telemetry error during exception handling: {telemetry_error}")

            # Re-raise the original exception
            raise

    def __getattr__(self, name):
        """Proxy undefined attributes to the original agent."""
        # Don't proxy methods we've already overridden
        if name in ('run', '__call__'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        return getattr(self._agent, name)


class TelemetryContext:
    """
    Context manager for automatic telemetry lifecycle management.

    This context manager handles the complete telemetry lifecycle:
    - Task creation and tracking setup
    - Agent instrumentation
    - Automatic cleanup on success or failure
    - Error isolation to prevent telemetry issues from affecting agent execution

    Usage:
        with telemetry_context(agent, "MyAgent", task, "sop_category") as instrumented_agent:
            result = instrumented_agent.run(task)
            return result
    """

    def __init__(
        self,
        agent,
        agent_name: str,
        task: str,
        sop_category: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None,
        task_type: Optional[str] = None,
    ):
        """
        Initialize telemetry context.

        Args:
            agent: The agent instance to instrument
            agent_name: Name of the agent for telemetry tracking
            task: Task description
            sop_category: SOP category for the task
            task_id: Optional task ID, will be generated if not provided
            agent_type: Type of agent (defaults to SUPERVISOR)
            task_type: Type of task being executed
        """
        self.agent = agent
        self.agent_name = agent_name
        self.task = task
        self.sop_category = sop_category
        self.task_id = task_id or f"{agent_name}_{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type or AgentType.SUPERVISOR
        self.task_type = task_type

        # Will be set during __enter__
        self.instrumented_agent = None
        self.telemetry_collector = None
        self.telemetry_manager = None
        self._telemetry_enabled = False

    def __enter__(self):
        """
        Enter the telemetry context and set up tracking.

        Returns:
            Instrumented agent or original agent if telemetry fails
        """
        try:
            # Get telemetry manager
            self.telemetry_manager = TelemetryManager.get_instance()

            # Initialize telemetry system if needed
            if not self.telemetry_manager.is_enabled():
                self.telemetry_manager.initialize()

            if not self.telemetry_manager.is_enabled():
                logger.debug("Telemetry is disabled, using original agent")
                self.instrumented_agent = self.agent
                return self.instrumented_agent

            # Get telemetry collector
            self.telemetry_collector = self.telemetry_manager.get_collector()
            if not self.telemetry_collector:
                logger.debug("No telemetry collector available, using original agent")
                self.instrumented_agent = self.agent
                return self.instrumented_agent

            # Start task tracking
            self.telemetry_collector.start_task(
                task_id=self.task_id,
                description=self.task,
                sop_category=self.sop_category,
                task_type=self.task_type,
            )

            logger.debug(f"Started telemetry task tracking: {self.task_id}")

            # Instrument the agent
            self.instrumented_agent = TelemetryInstrumentedAgent(
                agent=self.agent,
                agent_name=self.agent_name,
                agent_type=self.agent_type,
                telemetry_collector=self.telemetry_collector
            )

            self._telemetry_enabled = True
            logger.debug(f"Instrumented {self.agent_type.value} agent {self.agent_name} with telemetry")

            return self.instrumented_agent

        except Exception as e:
            # Telemetry setup failures should not block agent execution
            logger.warning(f"Failed to setup telemetry for agent {self.agent_name}: {e}")
            self.instrumented_agent = self.agent
            return self.instrumented_agent

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the telemetry context and clean up tracking.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            False to not suppress any exceptions
        """
        if not self._telemetry_enabled or not self.telemetry_collector:
            return False

        try:
            # Determine task status based on whether an exception occurred
            if exc_type is None:
                status = TaskStatus.COMPLETED
                error_message = None
            else:
                status = TaskStatus.FAILED
                error_message = str(exc_val) if exc_val else "Unknown error"

            # End task tracking
            self.telemetry_collector.end_task(
                self.task_id,
                status,
                error_message=error_message
            )

            logger.debug(f"Ended telemetry task tracking: {self.task_id} with status: {status}")

        except Exception as telemetry_error:
            # Telemetry cleanup errors should not mask the original exception
            logger.warning(f"Failed to cleanup telemetry for task {self.task_id}: {telemetry_error}")

        # Don't suppress any exceptions
        return False


def telemetry_context(
    agent,
    agent_name: str,
    task: str,
    sop_category: Optional[str] = None,
    task_id: Optional[str] = None,
    agent_type: Optional[AgentType] = None,
    task_type: Optional[str] = None,
) -> TelemetryContext:
    """
    Create a telemetry context manager for automatic telemetry lifecycle management.

    This is the main entry point for adding telemetry to agent execution.
    It provides a clean, context-manager-based API that handles all telemetry
    setup and cleanup automatically.

    Args:
        agent: The agent instance to instrument
        agent_name: Name of the agent for telemetry tracking
        task: Task description
        sop_category: SOP category for the task
        task_id: Optional task ID, will be generated if not provided
        agent_type: Type of agent (defaults to SUPERVISOR)
        task_type: Type of task being executed

    Returns:
        TelemetryContext instance for use with 'with' statement

    Example:
        with telemetry_context(agent, "CodeReviewAgent", task, "code_review") as instrumented_agent:
            result = instrumented_agent.run(task)
            return result
    """
    return TelemetryContext(
        agent=agent,
        agent_name=agent_name,
        task=task,
        sop_category=sop_category,
        task_id=task_id,
        agent_type=agent_type,
        task_type=task_type,
    )
