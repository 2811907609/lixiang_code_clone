"""
Tests for telemetry instrumentation functionality.

This module tests the AgentInstrumentor class and its ability to instrument
smolagents Model classes for automatic telemetry collection.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from ai_agents.telemetry.instrumentation import (
    AgentInstrumentor,
    instrument_smolagents_models
)
from ai_agents.telemetry.collector import TelemetryCollector
from ai_agents.telemetry.error_handler import TelemetryErrorHandler
from ai_agents.telemetry.types import LLMCall


class MockModel:
    """Mock Model class for testing instrumentation."""

    def __init__(self, model_id="test-model"):
        self.model_id = model_id

    def generate(self, messages, **kwargs):
        """Mock generate method."""
        # Simulate some processing time
        time.sleep(0.01)

        # Create a simple object instead of Mock for token usage
        class TokenUsage:
            def __init__(self):
                self.input_tokens = 10
                self.output_tokens = 20

        class Result:
            def __init__(self):
                self.token_usage = TokenUsage()
                self.content = "Test response"

        return Result()

    def generate_stream(self, messages, **kwargs):
        """Mock generate_stream method."""
        # Simulate streaming response
        for i in range(3):
            time.sleep(0.005)
            delta = Mock()
            delta.token_usage = Mock()
            delta.token_usage.input_tokens = 5 if i == 0 else 0
            delta.token_usage.output_tokens = 7
            delta.content = f"chunk_{i}"
            yield delta


class MockChatMessage:
    """Mock ChatMessage for testing."""

    def __init__(self, content="test", token_usage=None):
        self.content = content
        self.token_usage = token_usage or Mock()
        self.token_usage.input_tokens = 10
        self.token_usage.output_tokens = 15


class TestAgentInstrumentor:
    """Test cases for AgentInstrumentor class."""

    @pytest.fixture
    def mock_collector(self):
        """Create a mock TelemetryCollector."""
        return Mock(spec=TelemetryCollector)

    @pytest.fixture
    def mock_error_handler(self):
        """Create a mock TelemetryErrorHandler."""
        return Mock(spec=TelemetryErrorHandler)

    @pytest.fixture
    def instrumentor(self, mock_collector, mock_error_handler):
        """Create an AgentInstrumentor instance."""
        return AgentInstrumentor(mock_collector, mock_error_handler)

    def test_init(self, mock_collector, mock_error_handler):
        """Test AgentInstrumentor initialization."""
        instrumentor = AgentInstrumentor(mock_collector, mock_error_handler)

        assert instrumentor.collector == mock_collector
        assert instrumentor.error_handler == mock_error_handler
        assert instrumentor._original_methods == {}
        assert instrumentor._instrumented_classes == []

    def test_instrument_model_calls(self, instrumentor, mock_collector):
        """Test instrumenting a model class."""
        # Store original methods
        original_generate = MockModel.generate
        original_generate_stream = MockModel.generate_stream

        try:
            # Instrument the model class
            instrumented_class = instrumentor.instrument_model_calls(MockModel)

            # Verify the class is returned
            assert instrumented_class == MockModel

            # Verify methods are wrapped
            assert MockModel.generate != original_generate
            assert MockModel.generate_stream != original_generate_stream

            # Verify tracking
            assert MockModel in instrumentor._instrumented_classes
            assert len(instrumentor._original_methods) == 2

        finally:
            # Restore original methods
            MockModel.generate = original_generate
            MockModel.generate_stream = original_generate_stream

    def test_instrument_already_instrumented_class(self, instrumentor):
        """Test instrumenting an already instrumented class."""
        original_generate = MockModel.generate

        try:
            # Instrument twice
            instrumentor.instrument_model_calls(MockModel)
            instrumented_class = instrumentor.instrument_model_calls(MockModel)

            # Should return the class without error
            assert instrumented_class == MockModel

            # Should only be in the list once
            assert instrumentor._instrumented_classes.count(MockModel) == 1

        finally:
            MockModel.generate = original_generate

    def test_wrapped_generate_method(self, instrumentor, mock_collector):
        """Test that the wrapped generate method collects telemetry."""
        original_generate = MockModel.generate

        try:
            # Instrument the model
            instrumentor.instrument_model_calls(MockModel)

            # Create a model instance and call generate
            model = MockModel("test-model-id")
            messages = [{"role": "user", "content": "test"}]

            result = model.generate(messages)

            # Verify the result is returned correctly
            assert result.content == "Test response"

            # Verify telemetry was collected
            mock_collector.record_llm_call.assert_called_once()
            call_args = mock_collector.record_llm_call.call_args[0]

            # Should be called with an LLMCall object
            assert isinstance(call_args[0], LLMCall)
            llm_call = call_args[0]

            assert llm_call.model == "test-model-id"
            assert llm_call.prompt_tokens == 10
            assert llm_call.completion_tokens == 20
            assert llm_call.total_tokens == 30
            assert llm_call.duration > 0
            assert isinstance(llm_call.timestamp, datetime)

        finally:
            MockModel.generate = original_generate

    def test_wrapped_generate_stream_method(self, instrumentor, mock_collector):
        """Test that the wrapped generate_stream method collects telemetry."""
        original_generate_stream = MockModel.generate_stream

        try:
            # Instrument the model
            instrumentor.instrument_model_calls(MockModel)

            # Create a model instance and call generate_stream
            model = MockModel("stream-model-id")
            messages = [{"role": "user", "content": "test"}]

            # Consume the stream
            chunks = list(model.generate_stream(messages))

            # Verify we got the expected chunks
            assert len(chunks) == 3
            assert chunks[0].content == "chunk_0"

            # Verify telemetry was collected
            mock_collector.record_llm_call.assert_called_once()
            call_args = mock_collector.record_llm_call.call_args[0]

            # Should be called with an LLMCall object
            assert isinstance(call_args[0], LLMCall)
            llm_call = call_args[0]

            assert llm_call.model == "stream-model-id"
            # Should accumulate tokens from all chunks: 5 + 0 + 0 = 5 input, 7 * 3 = 21 output
            assert llm_call.prompt_tokens == 5
            assert llm_call.completion_tokens == 21
            assert llm_call.total_tokens == 26
            assert llm_call.duration > 0

        finally:
            MockModel.generate_stream = original_generate_stream

    def test_generate_method_exception_handling(self, instrumentor, mock_collector):
        """Test that exceptions in generate method are handled properly."""
        original_generate = MockModel.generate

        # Create a model that raises an exception
        def failing_generate(self, messages, **kwargs):
            time.sleep(0.01)
            raise ValueError("Test error")

        try:
            # Replace generate with failing version
            MockModel.generate = failing_generate

            # Instrument the model
            instrumentor.instrument_model_calls(MockModel)

            # Create a model instance and call generate
            model = MockModel("failing-model")
            messages = [{"role": "user", "content": "test"}]

            # Should raise the original exception
            with pytest.raises(ValueError, match="Test error"):
                model.generate(messages)

            # Verify telemetry was still collected for the failed call
            mock_collector.record_llm_call.assert_called_once()
            call_args = mock_collector.record_llm_call.call_args[0]

            assert isinstance(call_args[0], LLMCall)
            llm_call = call_args[0]

            assert llm_call.model == "failing-model"
            assert llm_call.prompt_tokens == 0  # Failed calls have zero tokens
            assert llm_call.completion_tokens == 0
            assert llm_call.total_tokens == 0
            assert llm_call.duration > 0

        finally:
            MockModel.generate = original_generate

    def test_generate_stream_exception_handling(self, instrumentor, mock_collector):
        """Test that exceptions in generate_stream method are handled properly."""
        original_generate_stream = MockModel.generate_stream

        # Create a stream that raises an exception
        def failing_generate_stream(self, messages, **kwargs):
            time.sleep(0.01)
            raise RuntimeError("Stream error")

        try:
            # Replace generate_stream with failing version
            MockModel.generate_stream = failing_generate_stream

            # Instrument the model
            instrumentor.instrument_model_calls(MockModel)

            # Create a model instance and call generate_stream
            model = MockModel("failing-stream-model")
            messages = [{"role": "user", "content": "test"}]

            # Should raise the original exception
            with pytest.raises(RuntimeError, match="Stream error"):
                list(model.generate_stream(messages))

            # Verify telemetry was still collected for the failed call
            mock_collector.record_llm_call.assert_called_once()
            call_args = mock_collector.record_llm_call.call_args[0]

            assert isinstance(call_args[0], LLMCall)
            llm_call = call_args[0]

            assert llm_call.model == "failing-stream-model"
            assert llm_call.prompt_tokens == 0  # Failed calls have zero tokens
            assert llm_call.completion_tokens == 0
            assert llm_call.total_tokens == 0
            assert llm_call.duration > 0

        finally:
            MockModel.generate_stream = original_generate_stream

    def test_uninstrument_all(self, instrumentor):
        """Test removing instrumentation from all classes."""
        original_generate = MockModel.generate
        original_generate_stream = MockModel.generate_stream

        try:
            # Instrument the model
            instrumentor.instrument_model_calls(MockModel)

            # Verify instrumentation
            assert MockModel.generate != original_generate
            assert MockModel.generate_stream != original_generate_stream
            assert len(instrumentor._instrumented_classes) == 1
            assert len(instrumentor._original_methods) == 2

            # Remove instrumentation
            instrumentor.uninstrument_all()

            # Verify restoration
            assert MockModel.generate == original_generate
            assert MockModel.generate_stream == original_generate_stream
            assert len(instrumentor._instrumented_classes) == 0
            assert len(instrumentor._original_methods) == 0

        finally:
            # Ensure cleanup
            MockModel.generate = original_generate
            MockModel.generate_stream = original_generate_stream

    def test_model_without_generate_stream(self, instrumentor, mock_collector):
        """Test instrumenting a model that doesn't have generate_stream method."""

        class SimpleModel:
            def __init__(self, model_id="simple-model"):
                self.model_id = model_id

            def generate(self, messages, **kwargs):
                result = Mock()
                result.token_usage = Mock()
                result.token_usage.input_tokens = 5
                result.token_usage.output_tokens = 10
                return result

        original_generate = SimpleModel.generate

        try:
            # Instrument the model
            instrumentor.instrument_model_calls(SimpleModel)

            # Verify only generate method is instrumented
            assert SimpleModel.generate != original_generate
            assert not hasattr(SimpleModel, 'generate_stream') or \
                   SimpleModel.generate_stream == getattr(SimpleModel, 'generate_stream', None)

            # Test that it works
            model = SimpleModel()
            model.generate([])

            # Verify telemetry collection
            mock_collector.record_llm_call.assert_called_once()

        finally:
            SimpleModel.generate = original_generate

    def test_instrumentation_error_handling(self, mock_collector, mock_error_handler):
        """Test that instrumentation errors are handled gracefully."""
        instrumentor = AgentInstrumentor(mock_collector, mock_error_handler)

        # Test that the instrumentor handles cases where methods don't exist gracefully
        class MinimalModel:
            pass  # No generate method

        # Attempt to instrument - should not crash
        result = instrumentor.instrument_model_calls(MinimalModel)

        # Should return the original class
        assert result == MinimalModel

        # The class should be tracked since instrumentation succeeded (even if no methods were wrapped)
        assert MinimalModel in instrumentor._instrumented_classes


class TestInstrumentSmolagentsModels:
    """Test cases for the instrument_smolagents_models function."""

    @pytest.fixture
    def mock_collector(self):
        """Create a mock TelemetryCollector."""
        return Mock(spec=TelemetryCollector)

    @pytest.fixture
    def mock_error_handler(self):
        """Create a mock TelemetryErrorHandler."""
        return Mock(spec=TelemetryErrorHandler)

    @patch('smolagents.models.Model')
    @patch('smolagents.models.LiteLLMModel')
    def test_instrument_smolagents_models_success(self, mock_litellm_model, mock_model,
                                                  mock_collector, mock_error_handler):
        """Test successful instrumentation of smolagents models."""
        # Mock the smolagents imports
        with patch('ai_agents.telemetry.instrumentation.AgentInstrumentor') as mock_instrumentor_class:
            mock_instrumentor = Mock()
            mock_instrumentor_class.return_value = mock_instrumentor

            # Call the function
            result = instrument_smolagents_models(mock_collector, mock_error_handler)

            # Verify instrumentor was created
            mock_instrumentor_class.assert_called_once_with(mock_collector, mock_error_handler)

            # Verify models were instrumented
            assert mock_instrumentor.instrument_model_calls.call_count >= 2

            # Verify the instrumentor is returned
            assert result == mock_instrumentor

    @patch('smolagents.models.Model')
    @patch('smolagents.models.LiteLLMModel')
    def test_instrument_smolagents_models_with_custom_model(self, mock_litellm_model, mock_model,
                                                           mock_collector, mock_error_handler):
        """Test instrumentation including custom LiteLLMModelV2."""
        # Mock the custom model import
        mock_custom_model = Mock()

        with patch('ai_agents.telemetry.instrumentation.AgentInstrumentor') as mock_instrumentor_class:
            mock_instrumentor = Mock()
            mock_instrumentor_class.return_value = mock_instrumentor

            with patch('ai_agents.lib.smolagents.models.LiteLLMModelV2', mock_custom_model):
                # Call the function
                instrument_smolagents_models(mock_collector, mock_error_handler)

                # Verify custom model was also instrumented
                assert mock_instrumentor.instrument_model_calls.call_count >= 3

    def test_instrument_smolagents_models_import_error(self, mock_collector, mock_error_handler):
        """Test handling of instrumentation errors during model instrumentation."""
        # Mock AgentInstrumentor to raise an exception during instrumentation
        with patch('ai_agents.telemetry.instrumentation.AgentInstrumentor') as mock_instrumentor_class:
            mock_instrumentor = Mock()
            mock_instrumentor.instrument_model_calls.side_effect = ImportError("Model instrumentation failed")
            mock_instrumentor_class.return_value = mock_instrumentor

            # Call the function
            result = instrument_smolagents_models(mock_collector, mock_error_handler)

            # Should still return an instrumentor
            assert isinstance(result, Mock)  # It's our mock instrumentor

            # Should have called error handler due to instrumentation failures
            assert mock_error_handler.handle_instrumentation_error.called

    def test_instrument_smolagents_models_missing_custom_model(self, mock_collector, mock_error_handler):
        """Test handling when custom LiteLLMModelV2 is not available."""
        with patch('smolagents.models.Model'):
            with patch('smolagents.models.LiteLLMModel'):
                with patch('ai_agents.telemetry.instrumentation.AgentInstrumentor') as mock_instrumentor_class:
                    mock_instrumentor = Mock()
                    mock_instrumentor_class.return_value = mock_instrumentor

                    # Make the custom model import fail
                    with patch('ai_agents.lib.smolagents.models.LiteLLMModelV2', side_effect=ImportError):
                        # Call the function
                        result = instrument_smolagents_models(mock_collector, mock_error_handler)

                        # Should still work and return instrumentor
                        assert result == mock_instrumentor

                        # Should have instrumented base models
                        assert mock_instrumentor.instrument_model_calls.call_count >= 2


class TestIntegrationWithTaskContext:
    """Test integration with existing task_context from ai_agents.lib.tracing."""

    @pytest.fixture
    def mock_collector(self):
        """Create a mock TelemetryCollector."""
        return Mock(spec=TelemetryCollector)

    @pytest.fixture
    def mock_error_handler(self):
        """Create a mock TelemetryErrorHandler."""
        return Mock(spec=TelemetryErrorHandler)

    @patch('ai_agents.telemetry.instrumentation.get_current_task_id')
    @patch('ai_agents.telemetry.instrumentation.get_current_agent_id')
    def test_task_context_integration(self, mock_get_agent_id, mock_get_task_id,
                                     mock_collector, mock_error_handler):
        """Test that instrumentation integrates with existing task context."""
        # Set up mock context
        mock_get_task_id.return_value = "test-task-123"
        mock_get_agent_id.return_value = "test-agent-456"

        instrumentor = AgentInstrumentor(mock_collector, mock_error_handler)
        original_generate = MockModel.generate

        try:
            # Instrument the model
            instrumentor.instrument_model_calls(MockModel)

            # Create a model instance and call generate
            model = MockModel("context-model")
            model.generate([{"role": "user", "content": "test"}])

            # Verify telemetry was collected
            mock_collector.record_llm_call.assert_called_once()

            # The instrumentation should work regardless of task context
            # (The actual integration with task context would be in the collector)

        finally:
            MockModel.generate = original_generate
