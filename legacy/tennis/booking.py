"""Booking helper — fills the reservation form and stops before payment.

SAFETY
------
This site takes a real $15 payment against a real permit. This module will, at
most, fill the *applicant* form and advance to the payment page. It NEVER enters
card details and NEVER completes a purchase — the user does that by hand.

Booking is opt-in (``confirm=True``); the default is a dry run that shows exactly
what would be submitted without sending anything.

The reserve id for a slot is re-resolved from a fresh availability fetch right
before submitting, so a stale token can't be POSTed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .client import TennisClient
from .config import BookingInfo
from .filters import Slot
from .parser import parse_availability


def verify_bookable_slots(
    client: TennisClient,
    slots: list[Slot],
    *,
    max_checks: int = 10,
    delay: float = 1.0,
    sleep=time.sleep,
) -> list[Slot]:
    """Drop slots the reserve endpoint reports as not actually bookable.

    A grid ``status2`` cell isn't a guarantee — some slots are taken, locked, or
    persistent false-positives. This GETs each slot's reserve page and keeps only
    those that aren't an explicit "not bookable" (``bookable`` and ``unknown`` are
    kept — never hide a slot on uncertainty). To stay polite it verifies at most
    ``max_checks`` slots, spaced by ``delay`` seconds; any extras pass through
    unverified.
    """
    kept: list[Slot] = []
    for i, slot in enumerate(slots):
        if i >= max_checks:
            kept.append(slot)
            continue
        if i > 0:
            sleep(delay)
        if client.check_bookable(slot.reserve_path) != "taken":
            kept.append(slot)
    return kept


def build_registration_payload(booking: BookingInfo, num_players: int = 2) -> dict:
    """Map :class:`BookingInfo` onto the ``registercp`` form fields."""
    payload = {
        "step": "register",
        "num_players": str(num_players),       # 2 = singles (1h), 4 = doubles (2h)
        "number1": booking.permit_number,      # Permit Number (player 1)
        "person_name1": booking.name,          # Name (player 1)
        "number2": booking.permit_number2,     # player 2 (doubles only)
        "person_name2": booking.name2,
        "email": booking.email,
        "address": booking.address,
        "address2": booking.apartment,         # Apartment (optional)
        "city": booking.city,
        "state": booking.state,                # optional
        "zip": booking.zip,
        "country": booking.country,
        "phone": booking.phone,
        "submit": "Continue to Payment",
    }
    return payload


def resolve_current_slot(client: TennisClient, target: Slot) -> Slot | None:
    """Re-fetch the target's park availability and return the live matching slot.

    Returns ``None`` if that court-hour is no longer bookable (taken or locked).
    """
    html = client.fetch_availability(target.park_id)
    for slot in parse_availability(html, park_id=target.park_id, park_name=target.park_name):
        if slot.key == target.key:
            return slot
    return None


@dataclass
class BookingResult:
    slot: Slot
    dry_run: bool
    submitted: bool
    reserve_url: str
    payload: dict
    payment_page_html: str | None = None  # only set on a confirmed submit
    note: str = ""


def book_slot(
    client: TennisClient,
    target: Slot,
    booking: BookingInfo,
    num_players: int = 2,
    confirm: bool = False,
) -> BookingResult:
    """Attempt to reach the payment step for ``target``.

    With ``confirm=False`` (default) nothing is sent — you get the payload and
    URL to review. With ``confirm=True`` the applicant form is submitted and the
    returned page is the payment step, which the user must finish manually.

    Auto-fill is only wired for Central Park's ``registercp`` form; for other
    parks it returns instructions to book via the live grid instead.
    """
    if "reservecp" not in target.reserve_path:
        return BookingResult(
            slot=target,
            dry_run=not confirm,
            submitted=False,
            reserve_url=target.reserve_url(client.base_url),
            payload={},
            note=f"Auto-fill booking is only wired for Central Park. For "
            f"{target.park_name}, open {target.grid_url(client.base_url)} and click "
            "the slot to book it yourself.",
        )

    current = resolve_current_slot(client, target)
    if current is None:
        return BookingResult(
            slot=target,
            dry_run=not confirm,
            submitted=False,
            reserve_url=target.reserve_url(client.base_url),
            payload={},
            note="Slot is no longer available (taken or locked). Nothing submitted.",
        )

    payload = build_registration_payload(booking, num_players)
    reserve_url = current.reserve_url(client.base_url)

    if not confirm:
        return BookingResult(
            slot=current,
            dry_run=True,
            submitted=False,
            reserve_url=reserve_url,
            payload=payload,
            note="DRY RUN — nothing submitted. Re-run with confirm=True to fill "
            "the form and reach the payment page (you complete payment manually).",
        )

    # Touch the reserve page first (mirrors the real click flow), then submit.
    client.fetch_reserve_form(current.reserve_path)
    payment_html = client.submit_registration(payload)
    return BookingResult(
        slot=current,
        dry_run=False,
        submitted=True,
        reserve_url=reserve_url,
        payload=payload,
        payment_page_html=payment_html,
        note="Applicant form submitted. You are now at the PAYMENT step — open "
        f"{reserve_url} in a browser and complete the $15 payment yourself.",
    )
