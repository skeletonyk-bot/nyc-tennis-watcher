"""Booking payload test — verifies the BookingInfo -> form-field mapping.

No network access: only the pure payload builder is exercised.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis.booking import build_registration_payload  # noqa: E402
from tennis.config import BookingInfo  # noqa: E402


def sample_booking():
    return BookingInfo(
        permit_number="CO-783330",
        name="Xiao Han Ji",
        email="angel_ji@live.ca",
        address="345 E 80th st",
        apartment="Unit 30B",
        city="New York",
        state="New York",
        zip="10075",
        country="United States",
        phone="6266167997",
    )


def test_singles_payload_maps_every_field():
    payload = build_registration_payload(sample_booking(), num_players=2)
    assert payload == {
        "step": "register",
        "num_players": "2",
        "number1": "CO-783330",
        "person_name1": "Xiao Han Ji",
        "number2": "",
        "person_name2": "",
        "email": "angel_ji@live.ca",
        "address": "345 E 80th st",
        "address2": "Unit 30B",
        "city": "New York",
        "state": "New York",
        "zip": "10075",
        "country": "United States",
        "phone": "6266167997",
        "submit": "Continue to Payment",
    }


def test_num_players_is_stringified():
    payload = build_registration_payload(sample_booking(), num_players=4)
    assert payload["num_players"] == "4"
