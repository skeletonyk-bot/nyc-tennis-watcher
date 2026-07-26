"""Configuration: booking applicant info + watcher settings.

Loaded from ``config.json`` (which holds PII and is git-ignored). See
``config.example.json`` for the schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@dataclass
class BookingInfo:
    """Applicant details used to fill the reservation form.

    Field names mirror the labels on the NYC Parks reservation form. The
    permit number + name belong to the *first* player (singles).
    """

    permit_number: str   # form field: number1   e.g. "CO-783330"
    name: str            # form field: person_name1
    email: str
    address: str
    city: str
    zip: str
    phone: str
    apartment: str = ""          # form field: address2 (optional)
    state: str = "New York"      # form field: state   (optional)
    country: str = "United States"

    # Second player, only used for doubles (num_players == 4).
    permit_number2: str = ""
    name2: str = ""


@dataclass
class Park:
    """A tennis facility in the reservation system."""

    id: int           # availability/{id}
    name: str         # display name in alerts

    def grid_url(self, base_url: str = "https://www.nycgovparks.org") -> str:
        return f"{base_url.rstrip('/')}/tennisreservation/availability/{self.id}"


@dataclass
class Settings:
    """Everything the watcher needs to run."""

    booking: BookingInfo
    parks: list[Park]                 # parks to watch (e.g. all of Manhattan)
    days_ahead: int = 7               # "the next week"
    exclude_hours: list[int] = field(default_factory=lambda: [14, 15])  # 2pm, 3pm
    num_players: int = 2              # 2 = singles (1 hour), 4 = doubles
    poll_interval_seconds: int = 180  # how often the watcher re-checks
    notify_webhook_url: str = ""      # optional: POST a JSON payload on new slots
    verify_before_alert: bool = True  # GET-check each slot is truly bookable first
    base_url: str = "https://www.nycgovparks.org"


def load_settings(path: str | Path | None = None) -> Settings:
    """Load :class:`Settings` from a JSON config file.

    Accepts either ``"parks": [{"id":.., "name":".."}, ...]`` (preferred) or a
    legacy single ``"park_id"`` / ``"park_name"`` pair.
    """
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found: {path}\n"
            "Copy config.example.json to config.json and fill it in."
        )
    data = json.loads(path.read_text())
    booking = BookingInfo(**data.pop("booking"))

    if "parks" in data:
        parks = [Park(**p) for p in data.pop("parks")]
    elif "park_id" in data:  # legacy single-park config
        parks = [Park(id=int(data.pop("park_id")), name=data.pop("park_name", "Central Park"))]
    else:
        parks = [Park(12, "Central Park")]
    data.pop("park_name", None)  # ignore a stray legacy key

    return Settings(booking=booking, parks=parks, **data)
