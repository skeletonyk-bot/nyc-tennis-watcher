"""Parser tests against a real saved availability page.

Ground truth is derived from the fixture itself (tests/fixtures/central_park.html,
a real Central Park availability snapshot), not from any external numbers.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis.parser import Slot, parse_availability, parse_time_to_hour  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "central_park.html")


def load_raw():
    with open(FIXTURE, encoding="utf-8") as fh:
        return fh.read()


def load():
    return parse_availability(load_raw())


SPORTIME = os.path.join(os.path.dirname(__file__), "fixtures", "sportime_randalls.html")


def test_letter_courts_and_reserve_path_for_non_central_park():
    # Sportime at Randall's Island uses letter courts (A-D) and /reserve/ (not /reservecp/).
    with open(SPORTIME, encoding="utf-8") as fh:
        slots = parse_availability(fh.read(), park_id=9, park_name="Sportime Randall's Island")
    assert slots, "expected bookable slots in the Sportime fixture"
    assert {s.court for s in slots} <= {"A", "B", "C", "D"}
    assert all(s.reserve_path.startswith("/tennisreservation/reserve/") for s in slots)
    assert all(s.park_id == 9 for s in slots)


def test_parses_expected_total():
    slots = load()
    assert len(slots) == 468


def test_known_slots_present_with_correct_fields():
    # (reserve_id, date, hour, time_label, court) read directly from the fixture HTML.
    expected = [
        ("953956", "2026-07-01", 15, "3:00 p.m.", "19"),
        ("954010", "2026-07-06", 14, "2:00 p.m.", "19"),
        ("954011", "2026-07-06", 15, "3:00 p.m.", "19"),
    ]
    by_id = {s.reserve_id: s for s in load()}
    for rid, date, hour, label, court in expected:
        assert rid in by_id, f"slot {rid} missing"
        s = by_id[rid]
        assert (s.date, s.hour, s.time_label, s.court) == (date, hour, label, court)
        assert s.reserve_path == f"/tennisreservation/reservecp/{rid}"


def test_slot_keys_are_unique():
    slots = load()
    keys = [s.key for s in slots]
    assert len(keys) == len(set(keys)), "duplicate (date, hour, court) keys"


def test_courts_in_expected_range():
    # Central Park online reservations are courts 19-24 (as string labels).
    assert {s.court for s in load()} <= {"19", "20", "21", "22", "23", "24"}


def test_slots_carry_park_identity():
    slots = parse_availability(load_raw(), park_id=12, park_name="Central Park")
    assert slots and all(s.park_id == 12 and s.park_name == "Central Park" for s in slots)
    assert slots[0].key[0] == 12  # park id is part of the dedup key


def test_time_parsing():
    cases = {
        "6:00 a.m.": 6, "12:00 p.m.": 12, "1:00 p.m.": 13,
        "12:00 a.m.": 0, "11:00 p.m.": 23, "2:00 p.m.": 14,
    }
    for label, hour in cases.items():
        assert parse_time_to_hour(label) == hour


def test_empty_html_yields_no_slots():
    assert parse_availability("<html></html>") == []


# --- robustness regressions -------------------------------------------------

def _grid(courts, rows):
    """Build a minimal calendar table. rows = list of (time_label, [cell_html...])."""
    head = "".join(f"<th>Court {c}</th>" for c in courts)
    body = ""
    for label, cells in rows:
        body += f"<tr><td><strong>{label}</strong></td>" + "".join(cells) + "</tr>"
    return (f'<table class="calendar table"><thead><tr><td></td>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table>")


def _reserve(rid):
    return f'<td class="status2"><a href="/tennisreservation/reservecp/{rid}">Reserve this time</a></td>'


def _booked():
    return '<td class="status3"><span>Booked</span></td>'


def test_tableless_pane_does_not_steal_next_days_table():
    # A "rained out" / closed day with no grid must not absorb the next day's table.
    html = (
        '<div id="2026-07-04" class="tab-pane"><h3>Closed</h3>'
        '<div class="rainedout">Rained Out</div></div>'
        '<div id="2026-07-05" class="tab-pane"><h3>Sunday</h3>'
        + _grid([19], [("1:00 p.m.", [_reserve("111")])])
        + "</div>"
    )
    slots = parse_availability(html)
    assert len(slots) == 1
    assert slots[0].date == "2026-07-05"  # NOT mis-attributed to 07-04
    assert slots[0].reserve_id == "111"


def test_tableless_last_pane_yields_nothing():
    html = '<div id="2026-07-05" class="tab-pane"><h3>x</h3><p>no grid</p></div>'
    assert parse_availability(html) == []


def test_column_count_mismatch_row_is_skipped_not_mislabeled():
    # 2 court headers but a row with 3 cells -> ambiguous mapping -> skip the row.
    bad_row = ("1:00 p.m.", [_reserve("1"), _reserve("2"), _reserve("3")])
    good_row = ("2:00 p.m.", [_reserve("4"), _booked()])
    html = ('<div id="2026-07-05" class="tab-pane">'
            + _grid([19, 20], [bad_row, good_row]) + "</div>")
    slots = parse_availability(html)
    # Only the well-formed row survives, with the correct court.
    assert len(slots) == 1
    assert (slots[0].court, slots[0].reserve_id) == ("19", "4")


def test_tr_with_attributes_is_parsed():
    html = ('<div id="2026-07-05" class="tab-pane"><table class="calendar">'
            '<thead><tr><td></td><th>Court 19</th></tr></thead><tbody>'
            '<tr class="odd"><td><strong>9:00 a.m.</strong></td>' + _reserve("7") +
            "</tr></tbody></table></div>")
    slots = parse_availability(html)
    assert len(slots) == 1 and slots[0].court == "19" and slots[0].hour == 9
