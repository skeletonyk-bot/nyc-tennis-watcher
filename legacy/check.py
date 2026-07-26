#!/usr/bin/env python3
"""One-shot availability check across all configured parks.

Fetches each park's availability, filters to the next week excluding 2pm/3pm,
and prints the matching open slots. Read-only — books nothing.

    python3 check.py
    python3 check.py --days 7 --exclude 14 15
    python3 check.py --verify          # confirm each match is *actually* bookable now
"""

from __future__ import annotations

import argparse
import sys

from tennis import TennisClient, load_settings, parse_availability, select_matching_slots
from tennis.booking import verify_bookable_slots
from tennis.notify import format_slots


def main() -> int:
    p = argparse.ArgumentParser(description="Check NYC tennis availability (read-only).")
    p.add_argument("--config", default=None, help="Path to config.json")
    p.add_argument("--days", type=int, default=None, help="Days ahead to scan (default from config)")
    p.add_argument("--exclude", type=int, nargs="*", default=None,
                   help="Hours (24h) to exclude, e.g. 14 15 for 2pm/3pm")
    p.add_argument("--verify", action="store_true",
                   help="GET-check each match and keep only those actually bookable right now")
    args = p.parse_args()

    settings = load_settings(args.config)
    days = args.days if args.days is not None else settings.days_ahead
    exclude = args.exclude if args.exclude is not None else settings.exclude_hours

    client = TennisClient(base_url=settings.base_url)
    all_slots = []
    for park in settings.parks:
        try:
            html = client.fetch_availability(park.id)
            slots = parse_availability(html, park_id=park.id, park_name=park.name)
            all_slots.extend(slots)
            print(f"  {park.name}: {len(slots)} bookable over its window")
        except Exception as exc:
            print(f"  {park.name}: fetch failed ({exc!r})")

    matches = select_matching_slots(all_slots, days_ahead=days, exclude_hours=exclude)
    print(f"\nNext {days} day(s), excluding hours {sorted(exclude)} — {len(matches)} match(es):\n")
    print(format_slots(matches))

    if args.verify and matches:
        print("\nVerifying each is actually bookable right now (grid can show false positives)...")
        bookable = verify_bookable_slots(client, matches)
        dead = [s for s in matches if s.key not in {b.key for b in bookable}]
        print(f"  {len(bookable)} confirmed bookable, {len(dead)} not bookable (false-positive / taken).")
        if dead:
            print("  Not bookable: " + "; ".join(str(s) for s in dead))
        matches = bookable

    if matches:
        print(f"\nReserve the earliest at: {matches[0].reserve_url(settings.base_url)}")
        print(f"Or open its live grid:   {matches[0].grid_url(settings.base_url)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
