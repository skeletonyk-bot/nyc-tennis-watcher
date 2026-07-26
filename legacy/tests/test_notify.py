"""Notifier tests — request building only, no network."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis import notify  # noqa: E402
from tennis.parser import Slot  # noqa: E402


def _slots():
    return [
        Slot("2026-07-02", 9, "9:00 a.m.", "22", "/tennisreservation/reservecp/957889"),
        Slot("2026-07-03", 17, "5:00 p.m.", "21", "/tennisreservation/reservecp/958000"),
    ]


def test_ntfy_request_shape():
    req = notify._ntfy_request("https://ntfy.sh/my-topic", _slots())
    assert req.method == "POST"
    headers = {k.lower(): v for k, v in req.header_items()}
    assert headers["title"] == "2 tennis court(s) open"
    assert headers["tags"] == "tennis"
    # Tapping opens the earliest slot's reservation page.
    assert headers["click"] == "https://www.nycgovparks.org/tennisreservation/reservecp/957889"
    body = req.data.decode()
    assert "Central Park — 2026-07-02 9:00 a.m. Court 22" in body
    assert "Central Park — 2026-07-03 5:00 p.m. Court 21" in body
    # Title must stay ASCII (ntfy header constraint).
    headers["title"].encode("ascii")


def test_ntfy_body_summarizes_when_many():
    slots = [
        Slot("2026-07-02", 9, "9:00 a.m.", str(i), f"/tennisreservation/reserve/{i}",
             park_id=9, park_name="Sportime")
        for i in range(20)
    ] + [Slot("2026-07-02", 8, "8:00 a.m.", "19", "/tennisreservation/reservecp/1",
              park_id=12, park_name="Central Park")]
    body = notify._ntfy_body(slots, cap=8)
    assert "20× Sportime" in body and "1× Central Park" in body
    assert "…and 13 more" in body          # 21 total - 8 shown
    assert body.count("\n") < 20           # not an exhaustive 21-line wall


def test_ntfy_body_lists_all_when_few():
    body = notify._ntfy_body(_slots(), cap=8)
    assert "…and" not in body and body.count("\n") == 1  # both slots, no summary


def test_ntfy_routing_vs_generic():
    slots = _slots()
    assert "Title" in dict(notify._ntfy_request("https://ntfy.sh/t", slots).header_items())
    generic = notify._generic_webhook_request("https://example.com/hook", slots)
    assert generic.get_header("Content-type") == "application/json"


def test_applescript_escape_neutralizes_backslash_and_quote():
    # A trailing backslash + quote must not break out of the AppleScript literal.
    assert notify._applescript_escape('a\\"b') == 'a\\\\\\"b'
