

import hashlib
import logging
import platform
import uuid

logger = logging.getLogger(__name__)

def get_machine_fingerprint() -> str:
    """
    Generate a machine fingerprint based on hardware and system characteristics.

    Returns:
        str: A consistent machine fingerprint hash
    """
    fingerprint_data = []

    try:
        # Basic system info
        fingerprint_data.append(platform.machine())
        fingerprint_data.append(platform.processor())
        fingerprint_data.append(platform.system())
        fingerprint_data.append(platform.release())

        # MAC address (most reliable hardware identifier)
        mac = hex(uuid.getnode())
        fingerprint_data.append(mac)

        # Hostname
        fingerprint_data.append(platform.node())

        # Additional system details
        fingerprint_data.append(platform.platform())

    except Exception as e:
        logger.warning(f"Error collecting machine fingerprint data: {e}")
        # Fallback to basic info
        fingerprint_data = [platform.system(), str(uuid.getnode())]

    # Create hash from collected data
    fingerprint_string = "|".join(str(item) for item in fingerprint_data)
    device_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()

    return device_hash[:16]  # Return first 16 characters for shorter ID
