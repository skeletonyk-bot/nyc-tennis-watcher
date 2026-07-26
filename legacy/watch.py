#!/usr/bin/env python3
"""Continuously watch for open slots across all configured parks ("always").

Polls every park in config.json on an interval. Each cycle it filters to the
next week excluding 2pm/3pm and notifies (console + macOS desktop + optional
webhook) about slots that are *newly* open since the last cycle. Read-only.

    python3 watch.py
    python3 watch.py --interval 120

Stop with Ctrl-C. Resilient to transient network/site errors (logs and backs off).

Dedup: a slot is announced once per process run and then remembered, so a slot
that briefly flickers (e.g. into the transient "Booking" lock state) is not
re-announced. A fresh run (such as the daily cron job) starts with an empty
memory and so reports everything currently open.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time

from tennis import TennisClient, load_settings, parse_availability, select_matching_slots
from tennis.booking import verify_bookable_slots
from tennis.client import FetchError
from tennis.notify import notify_new_slots


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def collect_matches(client, settings):
    """Fetch + parse + filter across all parks. Returns (matches, errors)."""
    all_slots = []
    errors = []
    for park in settings.parks:
        try:
            html = client.fetch_availability(park.id)
            all_slots.extend(parse_availability(html, park_id=park.id, park_name=park.name))
        except Exception as exc:
            errors.append((park, exc))
    matches = select_matching_slots(
        all_slots, days_ahead=settings.days_ahead, exclude_hours=settings.exclude_hours
    )
    return matches, errors


def main() -> int:
    p = argparse.ArgumentParser(description="Watch NYC tennis availability forever (read-only).")
    p.add_argument("--config", default=None, help="Path to config.json")
    p.add_argument("--interval", type=int, default=None,
                   help="Seconds between checks (default from config)")
    p.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    p.add_argument("--no-verify", action="store_true",
                   help="Skip the per-slot bookable check before alerting")
    args = p.parse_args()

    settings = load_settings(args.config)
    verify = settings.verify_before_alert and not args.no_verify
    interval = max(30, args.interval if args.interval is not None else settings.poll_interval_seconds)
    client = TennisClient(base_url=settings.base_url)

    park_names = ", ".join(pk.name for pk in settings.parks)
    print(f"Watching {len(settings.parks)} park(s) [{park_names}]: next {settings.days_ahead} "
          f"day(s), excluding hours {sorted(settings.exclude_hours)}, every {interval}s. Ctrl-C to stop.")

    notified: set = set()
    consecutive_errors = 0

    while True:
        try:
            matches, errors = collect_matches(client, settings)
            if errors and len(errors) == len(settings.parks):
                raise FetchError("; ".join(f"{pk.name}: {exc}" for pk, exc in errors))
            consecutive_errors = 0
            for pk, exc in errors:  # partial failures: log, keep going
                print(f"[{_now()}] {pk.name} fetch failed: {exc!r}", file=sys.stderr, flush=True)

            new_slots = [s for s in matches if s.key not in notified]
            if verify and new_slots:
                new_slots = verify_bookable_slots(client, new_slots)
            stamp = _now()
            if new_slots:
                print(f"[{stamp}] {len(matches)} match(es), {len(new_slots)} NEW & bookable:")
                notify_new_slots(new_slots, webhook_url=settings.notify_webhook_url,
                                 grid_url=new_slots[0].grid_url(settings.base_url))
                # Commit AFTER notifying, so a delivery hiccup doesn't drop a slot.
                notified.update(s.key for s in new_slots)
            else:
                print(f"[{stamp}] {len(matches)} match(es), nothing new to alert.", flush=True)

            if args.once:
                return 0

        except Exception as exc:  # FetchError or unexpected parser/shape error
            consecutive_errors += 1
            backoff = min(interval * consecutive_errors, 1800)
            kind = "fetch" if isinstance(exc, FetchError) else "unexpected"
            print(f"[{_now()}] {kind} error ({exc!r}); backing off {backoff}s.",
                  file=sys.stderr, flush=True)
            if args.once:
                return 1
            time.sleep(backoff)
            continue

        time.sleep(interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
