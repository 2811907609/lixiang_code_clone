"""
Tests for the ODS Event telemetry module.
"""

import os
import time
from unittest.mock import Mock, patch

import pytest
import requests
from externalapis.codingcopilot.odsevent import (
    DEFAULT_TIMEOUT,
    TELEMETRY_URL,
    TelemetryClient,
    TelemetryEvent,
    get_current_timestamp,
    send_telemetry_event,
)


class TestTelemetryEvent:
    """Test cases for TelemetryEvent dataclass."""

    def test_telemetry_event_creation_with_minimal_data(self):
        """Test creating a telemetry event with minimal required data."""
        event = TelemetryEvent(
            session_id="test-session-123",
            name="test_event",
            details={"key": "value"},
            module="sop_agents",
        )

        assert event.session_id == "test-session-123"
        assert event.name == "test_event"
        assert event.details == {"key": "value"}
        assert event.module == "sop_agents"
        assert event.seq == 1
        assert event.time is not None
        assert event.device_id is not None

    @patch('externalapis.codingcopilot.odsevent.get_device_info')
    @patch('externalapis.codingcopilot.odsevent.get_machine_fingerprint')
    def test_telemetry_event_auto_populates_device_info(self, mock_fingerprint, mock_device_info):
        """Test that device info is auto-populated when not provided."""
        mock_fingerprint.return_value = "test-fingerprint"
        mock_device_info.return_value = {
            "os_version": "10.15.7",
            "os_arch": "x86_64",
            "os_family": "Darwin",
            "brand": "Apple",
            "cpu_brand": "Intel Core i7",
            "cpu_cores": 8
        }

        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={},
            module="sop_agents",
        )

        assert event.device_id == "dev_test-fingerprint"
        assert event.device_os_version == "10.15.7"
        assert event.device_os_arch == "x86_64"
        assert event.device_os_family == "Darwin"
        assert event.device_brand == "Apple"
        assert event.device_cpu_brand == "Intel Core i7"
        assert event.device_cpu_cores == 8

    def test_telemetry_event_with_custom_values(self):
        """Test creating event with custom device values."""
        custom_time = int(time.time() * 1000)

        event = TelemetryEvent(
            session_id="custom-session",
            name="custom_event",
            details={"custom": "data"},
            module="custom_module",
            seq=5,
            time=custom_time,
            device_id="custom-device-id",
            device_os_version="11.0.0"
        )

        assert event.session_id == "custom-session"
        assert event.module == "custom_module"
        assert event.seq == 5
        assert event.time == custom_time
        assert event.device_id == "custom-device-id"
        assert event.device_os_version == "11.0.0"

    def test_date_utc_property(self):
        """Test date_utc property returns correct format."""
        # Use a known timestamp: 2023-01-15 12:30:45 UTC
        timestamp = 1673784645000  # milliseconds

        event = TelemetryEvent(
            session_id="test",
            name="test",
            details={},
            module="sop_agents",
            time=timestamp
        )

        assert event.date_utc == 20230115

    def test_hour_utc_property(self):
        """Test hour_utc property returns correct hour."""
        # Use a known timestamp: 2023-01-15 12:30:45 UTC
        timestamp = 1673784645000  # milliseconds

        event = TelemetryEvent(
            session_id="test",
            name="test",
            details={},
            module="sop_agents",
            time=timestamp
        )

        assert event.hour_utc == 12

    def test_uniq_id_property(self):
        """Test uniq_id property generates expected format."""
        event = TelemetryEvent(
            session_id="session-123",
            name="event_name",
            details={},
            module="sop_agents",
            time=1673784645000,
            seq=3
        )

        expected_id = "session-123:event_name:3"
        assert event.uniq_id == expected_id

    def test_to_dict_includes_all_fields(self):
        """Test to_dict method includes all fields and computed properties."""
        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={"test": "data"},
            module="sop_agents",
            time=1673784645000
        )

        event_dict = event.to_dict()

        # Check required fields
        assert event_dict["session_id"] == "test-session"
        assert event_dict["name"] == "test_event"
        assert event_dict["details"] == {"test": "data"}
        assert event_dict["time"] == 1673784645000

        # Check computed properties
        assert "date_utc" in event_dict
        assert "hour_utc" in event_dict
        assert "uniq_id" in event_dict


class TestTelemetryClient:
    """Test cases for TelemetryClient class."""

    def test_client_initialization_with_defaults(self):
        """Test client initialization with default values."""
        client = TelemetryClient()

        assert client.url == TELEMETRY_URL
        assert client.timeout == DEFAULT_TIMEOUT
        assert client.dry_run is False

    def test_client_initialization_with_custom_values(self):
        """Test client initialization with custom values."""
        custom_url = "https://custom.example.com/webhook"
        custom_timeout = 10

        client = TelemetryClient(url=custom_url, timeout=custom_timeout)

        assert client.url == custom_url
        assert client.timeout == custom_timeout

    @patch.dict(os.environ, {"DRY_RUN": "true"})
    def test_client_dry_run_mode_enabled(self):
        """Test client recognizes dry run mode from environment."""
        client = TelemetryClient()
        assert client.dry_run is True

    @patch.dict(os.environ, {"DRY_RUN": "false"})
    def test_client_dry_run_mode_disabled(self):
        """Test client dry run mode disabled."""
        client = TelemetryClient()
        assert client.dry_run is False

    @patch('requests.post')
    def test_send_event_success(self, mock_post):
        """Test successful event sending."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = TelemetryClient()
        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={"key": "value"},
            module="sop_agents",
        )

        result = client.send_event(event)

        assert result is True
        mock_post.assert_called_once()

        # Verify the call arguments
        call_args = mock_post.call_args
        assert call_args[1]['json'] == event.to_dict()
        assert call_args[1]['timeout'] == DEFAULT_TIMEOUT
        assert call_args[1]['headers'] == {"Content-Type": "application/json"}

    @patch('requests.post')
    def test_send_event_timeout_error(self, mock_post):
        """Test handling of timeout errors."""
        mock_post.side_effect = requests.exceptions.Timeout()

        client = TelemetryClient()
        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={},
            module="sop_agents",
        )

        result = client.send_event(event)

        assert result is False

    @patch('requests.post')
    def test_send_event_request_exception(self, mock_post):
        """Test handling of request exceptions."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        client = TelemetryClient()
        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={},
            module="sop_agents",
        )

        result = client.send_event(event)

        assert result is False

    @patch('requests.post')
    def test_send_event_http_error(self, mock_post):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        client = TelemetryClient()
        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={},
            module="sop_agents",
        )

        result = client.send_event(event)

        assert result is False

    @patch('requests.post')
    def test_send_event_unexpected_exception(self, mock_post):
        """Test handling of unexpected exceptions."""
        mock_post.side_effect = ValueError("Unexpected error")

        client = TelemetryClient()
        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={},
            module="sop_agents",
        )

        result = client.send_event(event)

        assert result is False

    @patch.dict(os.environ, {"DRY_RUN": "true"})
    def test_send_event_dry_run_mode(self):
        """Test event sending in dry run mode."""
        client = TelemetryClient()
        event = TelemetryEvent(
            session_id="test-session",
            name="test_event",
            details={},
            module="sop_agents",
        )

        with patch('requests.post') as mock_post:
            result = client.send_event(event)

            assert result is True
            mock_post.assert_not_called()


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_get_current_timestamp(self):
        """Test get_current_timestamp returns reasonable value."""
        timestamp = get_current_timestamp()

        # Should be a positive integer
        assert isinstance(timestamp, int)
        assert timestamp > 0

        # Should be close to current time (within 1 second)
        current_time_ms = int(time.time() * 1000)
        assert abs(timestamp - current_time_ms) < 1000

    @patch('externalapis.codingcopilot.odsevent._telemetry_client')
    def test_send_telemetry_event_success(self, mock_client):
        """Test send_telemetry_event function with successful sending."""
        mock_client.send_event.return_value = True

        result = send_telemetry_event(
            session_id="test-session",
            event_name="test_event",
            details={"key": "value"},
            module="sop_agents",
        )

        assert result is True
        mock_client.send_event.assert_called_once()

        # Verify the event passed to client
        event_arg = mock_client.send_event.call_args[0][0]
        assert event_arg.session_id == "test-session"
        assert event_arg.name == "test_event"
        assert event_arg.details == {"key": "value"}
        assert event_arg.module == "sop_agents"

    @patch('externalapis.codingcopilot.odsevent._telemetry_client')
    def test_send_telemetry_event_with_custom_module(self, mock_client):
        """Test send_telemetry_event with custom module."""
        mock_client.send_event.return_value = True

        result = send_telemetry_event(
            session_id="test-session",
            event_name="test_event",
            details={},
            module="custom_module"
        )

        assert result is True

        # Verify custom module is used
        event_arg = mock_client.send_event.call_args[0][0]
        assert event_arg.module == "custom_module"

    @patch('externalapis.codingcopilot.odsevent._telemetry_client')
    def test_send_telemetry_event_failure(self, mock_client):
        """Test send_telemetry_event function with sending failure."""
        mock_client.send_event.return_value = False

        result = send_telemetry_event(
            session_id="test-session",
            event_name="test_event",
            details={},
            module="sop_agents",
        )

        assert result is False


class TestIntegration:
    """Integration tests for the complete flow."""

    @patch('requests.post')
    @patch('externalapis.codingcopilot.odsevent.get_device_info')
    @patch('externalapis.codingcopilot.odsevent.get_machine_fingerprint')
    def test_end_to_end_telemetry_flow(self, mock_fingerprint, mock_device_info, mock_post):
        """Test complete telemetry flow from event creation to sending."""
        # Setup mocks
        mock_fingerprint.return_value = "test-fingerprint"
        mock_device_info.return_value = {
            "os_version": "10.15.7",
            "os_arch": "x86_64",
            "os_family": "Darwin",
            "brand": "Apple",
            "cpu_brand": "Intel Core i7",
            "cpu_cores": 8
        }

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Send telemetry event
        result = send_telemetry_event(
            session_id="integration-test-session",
            event_name="integration_test_event",
            details={"test_data": "integration_value", "count": 42},
            module="sop_agents",
        )

        # Verify success
        assert result is True

        # Verify HTTP request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Verify request details
        assert call_args[0][0] == TELEMETRY_URL
        assert call_args[1]['timeout'] == DEFAULT_TIMEOUT
        assert call_args[1]['headers'] == {"Content-Type": "application/json"}

        # Verify event data structure
        event_data = call_args[1]['json']
        assert event_data['session_id'] == "integration-test-session"
        assert event_data['name'] == "integration_test_event"
        assert event_data['details'] == {"test_data": "integration_value", "count": 42}
        assert event_data['module'] == "sop_agents"
        assert event_data['device_id'] == "dev_test-fingerprint"
        assert 'date_utc' in event_data
        assert 'hour_utc' in event_data
        assert 'uniq_id' in event_data


@pytest.fixture
def sample_event():
    """Fixture providing a sample telemetry event for testing."""
    return TelemetryEvent(
        session_id="fixture-session-123",
        name="fixture_event",
        details={"fixture": "data", "number": 123},
        module="sop_agents",
        time=1673784645000  # Fixed timestamp for consistent testing
    )


@pytest.fixture
def mock_telemetry_client():
    """Fixture providing a mocked telemetry client."""
    with patch('externalapis.codingcopilot.odsevent._telemetry_client') as mock_client:
        yield mock_client
