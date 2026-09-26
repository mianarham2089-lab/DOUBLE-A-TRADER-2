import os
from typing import Optional


def get_ssid(ssid: Optional[str] = None) -> str:
    """
    Get Quotex SSID from the supplied value
    or from the QUOTEX_SSID environment variable.
    """

    value = ssid or os.getenv("QUOTEX_SSID", "")

    return value.strip()


def validate_ssid(ssid: str) -> bool:
    """
    Basic check to make sure an SSID was provided.
    """

    if not ssid:
        return False

    return len(ssid.strip()) > 10
