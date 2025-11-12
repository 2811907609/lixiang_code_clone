import logging
import platform
from functools import lru_cache
from typing import Any, Dict

import psutil

logger = logging.getLogger(__name__)



@lru_cache(maxsize=1)
def get_cpu_brand() -> str:
    """
    Get CPU brand/model information.

    Returns:
        str: CPU brand name
    """
    try:
        # Try to get detailed CPU info
        processor = platform.processor()
        if processor:
            return processor

        # Fallback to machine type
        machine = platform.machine()
        if machine:
            return machine

        return "unknown"
    except Exception as e:
        logger.warning(f"Error getting CPU brand: {e}")
        return "unknown"



@lru_cache(maxsize=1)
def get_device_brand() -> str:
    """
    Get device brand/manufacturer information.

    Returns:
        str: Device brand
    """
    try:
        system = platform.system().lower()

        if system == "darwin":
            return "Apple"
        elif system == "windows":
            # Try to get manufacturer from WMI if available
            try:
                import subprocess
                result = subprocess.run(
                    ["wmic", "computersystem", "get", "manufacturer", "/value"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('Manufacturer='):
                        manufacturer = line.split('=', 1)[1].strip()
                        if manufacturer and manufacturer != "System manufacturer":
                            return manufacturer
            except Exception:
                pass
            return "PC"
        elif system == "linux":
            # Try to read DMI info
            try:
                with open('/sys/class/dmi/id/sys_vendor', 'r') as f:
                    vendor = f.read().strip()
                    if vendor and vendor not in ["System manufacturer", "To be filled by O.E.M."]:
                        return vendor
            except Exception:
                pass
            return "Linux PC"
        else:
            return platform.system()
    except Exception as e:
        logger.warning(f"Error getting device brand: {e}")
        return "unknown"



@lru_cache(maxsize=1)
def get_device_info() -> Dict[str, Any]:
    """
    Get comprehensive device information.

    Returns:
        Dict containing device information
    """
    try:
        info = {
            "os_version": platform.release(),
            "os_arch": platform.machine(),
            "os_family": platform.system(),
            "brand": get_device_brand(),
            "cpu_brand": get_cpu_brand(),
            "cpu_cores": psutil.cpu_count(logical=False) or psutil.cpu_count()
        }

        # Enhanced OS version for specific platforms
        system = platform.system().lower()
        if system == "darwin":
            # macOS version
            try:
                mac_version = platform.mac_ver()[0]
                if mac_version:
                    info["os_version"] = mac_version
            except Exception:
                pass
        elif system == "windows":
            # Windows version
            try:
                win_version = platform.win32_ver()[0]
                if win_version:
                    info["os_version"] = win_version
            except Exception:
                pass
        elif system == "linux":
            # Linux distribution info
            try:
                import distro
                info["os_version"] = f"{distro.name()} {distro.version()}"
                info["os_family"] = "Linux"
            except ImportError:
                # Fallback without distro package
                try:
                    with open('/etc/os-release', 'r') as f:
                        os_release = f.read()
                        for line in os_release.split('\n'):
                            if line.startswith('PRETTY_NAME='):
                                pretty_name = line.split('=', 1)[1].strip('"')
                                info["os_version"] = pretty_name
                                break
                except Exception:
                    pass

        return info

    except Exception as e:
        logger.warning(f"Error collecting device info: {e}")
        return {
            "os_version": "unknown",
            "os_arch": "unknown",
            "os_family": "unknown",
            "brand": "unknown",
            "cpu_brand": "unknown",
            "cpu_cores": 0
        }
