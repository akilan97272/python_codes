from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class Event:
    source: str
    subtype: str
    ts: float
    host: str
    os: str
    data: Dict[str, Any]
