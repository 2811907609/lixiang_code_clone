"""
ODS Event telemetry module for sending events to the telemetry service.

This module provides a clean interface for sending telemetry events with proper
error handling, logging, and data validation.
"""

import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import requests
from commonlibs.deviceinfo import get_device_info, get_machine_fingerprint

logger = logging.getLogger(__name__)

# Telemetry service configuration
TELEMETRY_URL = "https://portal-k8s-prod.ep.chehejia.com/webhook-receiver/v1.0/invoke/webhook-receiver/method/webhook-receiver?uuid=d9000b78-4571-11ef-9190-32b8cfa558c5&name=codebuddy-telemetry-events-01"
DEFAULT_TIMEOUT = 5


@dataclass
class TelemetryEvent:
    """Represents a telemetry event with all required fields."""

    session_id: str
    name: str
    details: Dict[str, Any]
    module: str
    seq: int = 1
    time: Optional[int] = None
    device_id: Optional[str] = None
    device_os_version: Optional[str] = None
    device_os_arch: Optional[str] = None
    device_os_family: Optional[str] = None
    device_brand: Optional[str] = None
    device_cpu_brand: Optional[str] = None
    device_cpu_cores: Optional[int] = None

    def __post_init__(self):
        """Initialize computed fields after object creation."""
        if self.time is None:
            self.time = get_current_timestamp()
        if self.device_id is None:
            self.device_id = f"dev_{get_machine_fingerprint()}"

        # Auto-populate device info if not provided
        device_info = get_device_info()
        if self.device_os_version is None:
            self.device_os_version = device_info.get("os_version")
        if self.device_os_arch is None:
            self.device_os_arch = device_info.get("os_arch")
        if self.device_os_family is None:
            self.device_os_family = device_info.get("os_family")
        if self.device_brand is None:
            self.device_brand = device_info.get("brand")
        if self.device_cpu_brand is None:
            self.device_cpu_brand = device_info.get("cpu_brand")
        if self.device_cpu_cores is None:
            self.device_cpu_cores = device_info.get("cpu_cores")

    @property
    def date_utc(self) -> int:
        """Get UTC date in YYYYMMDD format."""
        return int(time.strftime("%Y%m%d", time.gmtime(self.time / 1000)))

    @property
    def hour_utc(self) -> int:
        """Get UTC hour (0-23)."""
        return time.gmtime(self.time / 1000).tm_hour

    @property
    def uniq_id(self) -> str:
        """Generate unique identifier for this event."""
        return f"{self.session_id}:{self.name}:{self.seq}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format for API submission."""
        data = asdict(self)
        # Add computed properties
        data.update({
            "date_utc": self.date_utc,
            "hour_utc": self.hour_utc,
            "uniq_id": self.uniq_id
        })
        return data


class TelemetryClient:
    """Client for sending telemetry events to the ODS service."""

    def __init__(self, url: str = TELEMETRY_URL, timeout: int = DEFAULT_TIMEOUT):
        self.url = url
        self.timeout = timeout
        self.dry_run = os.environ.get("DRY_RUN", "").lower() in ("true", "1", "yes")

    def send_event(self, event: TelemetryEvent) -> bool:
        """
        Send a telemetry event to the service.

        Args:
            event: The telemetry event to send

        Returns:
            bool: True if successful, False otherwise
        """
        event_data = event.to_dict()

        logger.info(f"Sending telemetry event: {event.name} (session: {event.session_id})")
        logger.debug(f"Event data: {event_data}")

        if self.dry_run:
            logger.info("DRY_RUN mode: Event not actually sent")
            return True

        try:
            response = requests.post(
                self.url,
                json=event_data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            logger.info(f"Successfully sent telemetry event: {event.uniq_id}")
            return True

        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending telemetry event: {event.uniq_id}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending telemetry event {event.uniq_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending telemetry event {event.uniq_id}: {e}")
            return False


# Global client instance
_telemetry_client = TelemetryClient()


def get_current_timestamp() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def send_telemetry_event(
    session_id: str,
    event_name: str,
    details: Dict[str, Any],
    module: str,
) -> bool:
    """
    Send a telemetry event with the given parameters.

    Args:
        session_id: Unique session identifier
        event_name: Name of the event
        details: Event details/payload
        module: Module name (defaults to 'codedoggy')

    Returns:
        bool: True if successful, False otherwise
    """
    event = TelemetryEvent(
        session_id=session_id,
        name=event_name,
        details=details,
        module=module
    )

    return _telemetry_client.send_event(event)
