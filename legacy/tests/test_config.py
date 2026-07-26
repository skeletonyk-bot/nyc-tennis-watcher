"""Config loader tests — multi-park and legacy single-park shapes."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis.config import load_settings  # noqa: E402

_BOOKING = {
    "permit_number": "CO-1", "name": "T", "email": "t@x.co",
    "address": "1 St", "city": "NY", "zip": "10000", "phone": "5550000",
}


def _write(cfg):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(cfg, fh)
    return path


def test_loads_multi_park():
    path = _write({
        "parks": [{"id": 12, "name": "Central Park"}, {"id": 3, "name": "Riverside Clay"}],
        "days_ahead": 7, "booking": _BOOKING,
    })
    s = load_settings(path)
    assert [(p.id, p.name) for p in s.parks] == [(12, "Central Park"), (3, "Riverside Clay")]
    assert s.parks[0].grid_url("https://x").endswith("/tennisreservation/availability/12")
    os.unlink(path)


def test_legacy_single_park_still_loads():
    path = _write({"park_id": 12, "park_name": "Central Park", "booking": _BOOKING})
    s = load_settings(path)
    assert len(s.parks) == 1 and s.parks[0].id == 12 and s.parks[0].name == "Central Park"
    os.unlink(path)
