"""Filter tests: 'next week' window + 2pm/3pm exclusion.

The fixture was captured on 2026-06-26, so we pin ``today`` to that date to make
the window deterministic.
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis.filters import select_matching_slots, today_in_nyc, within_next_week  # noqa: E402
from tennis.parser import parse_availability  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "central_park.html")
TODAY = dt.date(2026, 6, 26)  # date the fixture was captured


def load():
    with open(FIXTURE, encoding="utf-8") as fh:
        return parse_availability(fh.read())


def test_within_next_week_boundaries():
    # today is excluded (no same-day reservations); window is (today, today+7].
    assert not within_next_week("2026-06-26", TODAY, 7)   # today
    assert within_next_week("2026-06-27", TODAY, 7)       # tomorrow
    assert within_next_week("2026-07-03", TODAY, 7)       # +7, last day
    assert not within_next_week("2026-07-04", TODAY, 7)   # +8, too far


def test_matches_are_in_window_and_not_excluded():
    matches = select_matching_slots(load(), days_ahead=7, exclude_hours=(14, 15), today=TODAY)
    assert matches, "expected at least one match in the next week"
    for s in matches:
        assert within_next_week(s.date, TODAY, 7)
        assert s.hour not in (14, 15)


def test_excludes_2pm_3pm_specifically():
    matches = select_matching_slots(load(), days_ahead=7, exclude_hours=(14, 15), today=TODAY)
    keys = {s.key for s in matches}
    # 953956 is a 3pm (hour 15) slot on 2026-07-01 — inside the window but excluded.
    # key = (park_id, date, hour, court)
    assert (12, "2026-07-01", 15, "19") not in keys
    # ...and there are no 2pm/3pm slots at all in the result.
    assert not any(s.hour in (14, 15) for s in matches)


def test_in_window_non_excluded_slot_is_kept():
    all_slots = load()
    # Find a real slot inside the window with an allowed hour, assert it survives.
    sample = next(
        s for s in all_slots
        if within_next_week(s.date, TODAY, 7) and s.hour not in (14, 15)
    )
    matches = select_matching_slots(all_slots, days_ahead=7, exclude_hours=(14, 15), today=TODAY)
    assert sample.key in {s.key for s in matches}


def test_results_are_sorted():
    matches = select_matching_slots(load(), days_ahead=7, exclude_hours=(14, 15), today=TODAY)
    assert matches == sorted(matches, key=lambda s: (s.date, s.hour, s.park_name, s.court))


def test_default_today_is_a_date_and_filter_runs_without_explicit_today():
    assert isinstance(today_in_nyc(), dt.date)
    # Should not raise when today is omitted (uses the NYC default).
    select_matching_slots(load(), days_ahead=7, exclude_hours=(14, 15))
