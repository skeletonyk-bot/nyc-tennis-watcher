"""Tests for bookability verification + the grid-fallback alert. No network."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis import notify  # noqa: E402
from tennis.booking import verify_bookable_slots  # noqa: E402
from tennis.parser import Slot  # noqa: E402


class FakeClient:
    """Stand-in for TennisClient.check_bookable, driven by a verdict map."""

    def __init__(self, verdicts):
        self.verdicts = verdicts          # reserve_id -> "bookable"|"taken"|"unknown"
        self.checked = []

    def check_bookable(self, reserve_path):
        rid = reserve_path.rsplit("/", 1)[-1]
        self.checked.append(rid)
        return self.verdicts.get(rid, "unknown")


def _slots():
    return [
        Slot("2026-07-02", 9, "9:00 a.m.", "22", "/tennisreservation/reserve/A"),   # bookable
        Slot("2026-07-02", 10, "10:00 a.m.", "22", "/tennisreservation/reserve/B"),  # taken
        Slot("2026-07-03", 17, "5:00 p.m.", "21", "/tennisreservation/reserve/C"),   # unknown
    ]


def test_verify_drops_only_taken_slots():
    client = FakeClient({"A": "bookable", "B": "taken", "C": "unknown"})
    kept = verify_bookable_slots(client, _slots(), delay=0, sleep=lambda *_: None)
    ids = [s.reserve_id for s in kept]
    assert ids == ["A", "C"]            # 'taken' dropped; 'bookable' and 'unknown' kept


def test_verify_respects_max_checks_and_passes_extras_through():
    slots = _slots()
    client = FakeClient({"A": "taken", "B": "taken", "C": "taken"})
    # Only verify the first slot; the rest pass through unverified (kept).
    kept = verify_bookable_slots(client, slots, max_checks=1, delay=0, sleep=lambda *_: None)
    assert client.checked == ["A"]      # only one network check
    assert [s.reserve_id for s in kept] == ["B", "C"]  # A dropped (taken), B/C unchecked->kept


def test_ntfy_request_adds_grid_action_button():
    slots = _slots()
    grid = "https://www.nycgovparks.org/tennisreservation/availability/12"
    req = notify._ntfy_request("https://ntfy.sh/t", slots, grid_url=grid)
    headers = {k.lower(): v for k, v in req.header_items()}
    assert headers["actions"] == f"view, Open live grid, {grid}"
    assert "not bookable" in req.data.decode().lower()  # body has the fallback hint


def test_ntfy_request_no_action_when_grid_missing():
    req = notify._ntfy_request("https://ntfy.sh/t", _slots())
    headers = {k.lower(): v for k, v in req.header_items()}
    assert "actions" not in headers
