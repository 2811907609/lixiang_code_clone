"""
Simple remote telemetry sender for sending session data to external services.
"""

import logging

from .types import TelemetrySession

from externalapis.codingcopilot.odsevent import send_telemetry_event

from ai_agents.core.runtime import runtime


logger = logging.getLogger(__name__)


def send_session_to_remote(session: TelemetrySession) -> bool:
    """
    Send telemetry session data to remote service.

    Args:
        session: TelemetrySession to send

    Returns:
        bool: True if successful or initiated
    """
    if not session:
        return False
    try:
        # Convert session to simple dict for sending
        session_data = session.to_dict()

        event_name = f"{runtime.app}:agent-stats"
        return send_telemetry_event(
            session_id=session.session_id,
            event_name=event_name,
            details=session_data,
            module="sop_agents"
        )

    except Exception as e:
        logger.error(f"Failed to send session {session.session_id}: {e}")
        return False
