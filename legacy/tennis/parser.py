"""Parse a NYC Parks tennis availability page into structured slots.

Works across all parks, which differ in ways the parser must tolerate:

* Central Park's grid table is ``class="calendar table table-bordered"``; other
  parks use ``class="table table-bordered"`` — so we don't key on the class.
* Central Park bookable links are ``/tennisreservation/reservecp/{id}``; other
  parks use ``/tennisreservation/reserve/{id}`` — we capture the whole path.
* Court labels are usually numbers ("19") but can be letters (Sportime's
  "A".."D") — so ``Slot.court`` is a string.
* Central Park advertises 30 days; others 7. The booking-window filter handles
  that downstream.

Each day is a ``<div id="YYYY-MM-DD" class="tab-pane">`` containing one grid
table. A bookable cell wraps an anchor whose href is the reserve path; the
trailing integer is a stable per-slot id. We key slots by
``(park_id, date, court, hour)`` and re-resolve the id at booking time, so a
stale id can never be POSTed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PANE_START_RE = re.compile(r'id="(\d{4}-\d{2}-\d{2})"[^>]*>')
_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.DOTALL)
_COURT_HEADER_RE = re.compile(r"<th[^>]*>\s*Court\s+([^<]+?)\s*</th>", re.IGNORECASE)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
_TIME_RE = re.compile(r"<strong>\s*([^<]+?)\s*</strong>")
_RESERVE_RE = re.compile(r"(/tennisreservation/reserve(?:cp)?/\d+)")


@dataclass(frozen=True)
class Slot:
    """One bookable court-hour at a specific park."""

    date: str           # "2026-06-29"
    hour: int           # 24-hour, e.g. 14 for 2:00 p.m.
    time_label: str     # "2:00 p.m."
    court: str          # "21" or "A"
    reserve_path: str   # "/tennisreservation/reserve(cp)/959169"
    park_id: int = 12
    park_name: str = "Central Park"

    @property
    def reserve_id(self) -> str:
        return self.reserve_path.rsplit("/", 1)[-1]

    @property
    def key(self) -> tuple[int, str, int, str]:
        """Stable identity independent of the reserve id."""
        return (self.park_id, self.date, self.hour, self.court)

    def reserve_url(self, base_url: str = "https://www.nycgovparks.org") -> str:
        return base_url.rstrip("/") + self.reserve_path

    def grid_url(self, base_url: str = "https://www.nycgovparks.org") -> str:
        return f"{base_url.rstrip('/')}/tennisreservation/availability/{self.park_id}"

    def __str__(self) -> str:
        return f"{self.park_name}: {self.date} {self.time_label:>10}  Court {self.court}"


def parse_time_to_hour(label: str) -> int:
    """Convert '6:00 a.m.' / '12:00 p.m.' / '1:00 p.m.' to a 24-hour int."""
    m = re.match(r"\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?", label, re.IGNORECASE)
    if not m:
        raise ValueError(f"Unrecognized time label: {label!r}")
    hour = int(m.group(1)) % 12
    if m.group(3).lower() == "p":
        hour += 12
    return hour


def _pane_segments(html: str):
    """Yield (date, html_segment) for each day, segment bounded by its own pane."""
    starts = list(_PANE_START_RE.finditer(html))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(html)
        yield m.group(1), html[m.end():end]


def parse_availability(
    html: str, *, park_id: int = 12, park_name: str = "Central Park"
) -> list[Slot]:
    """Return every bookable :class:`Slot` on an availability page."""
    slots: list[Slot] = []
    for date, segment in _pane_segments(html):
        table_match = _TABLE_RE.search(segment)
        if not table_match:
            continue  # day with no grid (closed / rained out) -> no slots
        table = table_match.group(0)

        courts = [c.strip() for c in _COURT_HEADER_RE.findall(table)]
        if not courts:
            continue

        for row_match in _ROW_RE.finditer(table):
            row = row_match.group(1)
            time_match = _TIME_RE.search(row)
            if not time_match:
                continue  # header row or non-data row
            time_label = time_match.group(1).strip()
            try:
                hour = parse_time_to_hour(time_label)
            except ValueError:
                continue

            cells = _TD_RE.findall(row)
            court_cells = cells[1:]  # first cell is the time label
            if len(court_cells) != len(courts):
                # Column count disagrees with the header: don't risk mislabeling.
                continue

            for idx, inner in enumerate(court_cells):
                reserve = _RESERVE_RE.search(inner)
                if reserve:
                    slots.append(
                        Slot(
                            date=date,
                            hour=hour,
                            time_label=time_label,
                            court=courts[idx],
                            reserve_path=reserve.group(1),
                            park_id=park_id,
                            park_name=park_name,
                        )
                    )
    return slots
