"""Select the slots the user actually cares about.

The request: availability in *the next week* for *non-2pm/3pm* time slots.

  * "next week"  -> dates from tomorrow through ``today + days_ahead`` inclusive.
    Same-day reservations are not allowed by the site, so today is excluded.
  * "non 2pm/3pm" -> drop any slot whose hour is in ``exclude_hours`` (14, 15).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable

try:
    from zoneinfo import ZoneInfo
    _NYC = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - zoneinfo/tzdata unavailable
    _NYC = None

from .parser import Slot


def today_in_nyc() -> _dt.date:
    """Current calendar date in the park's timezone (America/New_York).

    The courts are in NYC, so the booking window must be anchored there — a
    watcher running on a UTC host would otherwise shift the window after ~8pm ET.
    """
    if _NYC is not None:
        return _dt.datetime.now(_NYC).date()
    return _dt.date.today()


def within_next_week(date: str, today: _dt.date, days_ahead: int) -> bool:
    """True if ``date`` (YYYY-MM-DD) is in (today, today + days_ahead]."""
    d = _dt.date.fromisoformat(date)
    return today < d <= today + _dt.timedelta(days=days_ahead)


def select_matching_slots(
    slots: Iterable[Slot],
    *,
    days_ahead: int = 7,
    exclude_hours: Iterable[int] = (14, 15),
    today: _dt.date | None = None,
) -> list[Slot]:
    """Filter to next-week, non-excluded-hour slots, sorted chronologically."""
    today = today or today_in_nyc()
    excluded = set(exclude_hours)
    matches = [
        s
        for s in slots
        if s.hour not in excluded and within_next_week(s.date, today, days_ahead)
    ]
    matches.sort(key=lambda s: (s.date, s.hour, s.park_name, s.court))
    return matches
