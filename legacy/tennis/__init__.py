"""NYC Parks tennis court availability watcher (multi-park)."""

from .client import TennisClient
from .config import BookingInfo, Park, Settings, load_settings
from .filters import select_matching_slots, within_next_week
from .parser import Slot, parse_availability

__all__ = [
    "TennisClient",
    "BookingInfo",
    "Park",
    "Settings",
    "load_settings",
    "select_matching_slots",
    "within_next_week",
    "Slot",
    "parse_availability",
]
