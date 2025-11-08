"""
Asset creation types.
Used for camera asset upload initiation.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Asset:
    """Asset creation request from camera."""
    name: str
    filetype: str
    filesize: int
    parts: int
    offset: Optional[int] = field(default=None)

