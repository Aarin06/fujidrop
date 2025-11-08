"""
Device authentication types.
Used for camera device authentication flow.
"""
from dataclasses import dataclass


@dataclass
class DeviceCode:
    """Device authentication code request."""
    client_id: str
    client_secret: str
    scope: str

