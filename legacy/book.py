#!/usr/bin/env python3
"""Opt-in booking helper — reaches the payment step, never pays.

By default this is a DRY RUN: it locates a slot and prints exactly what would be
submitted, sending nothing. Pass --confirm to actually fill the applicant form
and advance to the payment page, which you must then complete by hand in a
browser. Card details and the $15 charge are never automated.

    # See the first matching slot and the payload (sends nothing):
    python3 book.py --first

    # Target a specific slot:
    python3 book.py --date 2026-06-29 --hour 13 --court 24

    # Actually fill the form and reach payment (you finish payment yourself):
    python3 book.py --date 2026-06-29 --hour 13 --court 24 --confirm
"""

from __future__ import annotations

import argparse
import sys

from tennis import TennisClient, load_settings, parse_availability, select_matching_slots
from tennis.booking import book_slot


def main() -> int:
    p = argparse.ArgumentParser(description="Book a slot up to (not including) payment.")
    p.add_argument("--config", default=None)
    p.add_argument("--first", action="store_true",
                   help="Target the first matching slot (next week, non-2pm/3pm)")
    p.add_argument("--date", help="YYYY-MM-DD")
    p.add_argument("--hour", type=int, help="24-hour, e.g. 13 for 1pm")
    p.add_argument("--court", help="Court label, e.g. 19 or A")
    p.add_argument("--park", type=int, help="Restrict to a park id (e.g. 12 for Central Park)")
    p.add_argument("--confirm", action="store_true",
                   help="Actually submit the applicant form and reach the payment page")
    args = p.parse_args()

    settings = load_settings(args.config)
    client = TennisClient(base_url=settings.base_url)

    parks = [pk for pk in settings.parks if args.park is None or pk.id == args.park]
    all_slots = []
    for park in parks:
        try:
            html = client.fetch_availability(park.id)
            all_slots.extend(parse_availability(html, park_id=park.id, park_name=park.name))
        except Exception as exc:
            print(f"{park.name}: fetch failed ({exc!r})")

    if args.first:
        matches = select_matching_slots(
            all_slots, days_ahead=settings.days_ahead, exclude_hours=settings.exclude_hours
        )
        if not matches:
            print("No matching slots available right now.")
            return 1
        target = matches[0]
    elif args.date and args.hour is not None and args.court is not None:
        target = next(
            (s for s in all_slots
             if s.date == args.date and s.hour == args.hour and s.court == str(args.court)),
            None,
        )
        if target is None:
            print(f"No bookable slot for {args.date} hour {args.hour} court {args.court}.")
            return 1
    else:
        p.error("Specify --first, or all of --date --hour --court.")
        return 2

    print(f"Target slot: {target}")
    result = book_slot(
        client, target, settings.booking,
        num_players=settings.num_players, confirm=args.confirm,
    )

    print(f"\nReserve URL: {result.reserve_url}")
    if result.payload:
        print("Form payload that " + ("WAS" if result.submitted else "would be") + " submitted:")
        for k, v in result.payload.items():
            print(f"    {k:14} = {v}")
    print(f"\n{result.note}")

    if not args.confirm:
        print("\n(Dry run. Add --confirm to fill the form and reach the payment page.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
