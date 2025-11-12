import os
from dataclasses import dataclass, field


@dataclass
class Config:
    PORTAL_BASE_URL: str = field(
        default_factory=lambda: os.getenv('PORTAL_BASE_URL', ''))
    PORTAL_TOKEN: str = field(
        default_factory=lambda: os.getenv('PORTAL_TOKEN', ''))
