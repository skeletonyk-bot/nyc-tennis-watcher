"""Notifications for newly-found slots.

Channels (best-effort; failures never raise):
  * Console  — always.
  * macOS desktop banner via ``osascript`` — note this is unreliable when invoked
    from a launchd agent, so don't rely on it as the only channel.
  * Webhook — if ``notify_webhook_url`` is set. An ``ntfy.sh`` URL gets a proper
    push (title + 🎾 tag + tap-to-open booking link); any other URL gets a
    generic JSON POST.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import urllib.request
from collections.abc import Iterable

from .parser import Slot


def format_slots(slots: Iterable[Slot]) -> str:
    slots = list(slots)
    if not slots:
        return "(no matching slots)"
    lines = [str(s) for s in slots]
    return "\n".join(lines)


def _applescript_escape(s: str) -> str:
    # Escape backslashes FIRST, then quotes — otherwise a backslash in the input
    # would break out of the AppleScript string literal.
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _macos_notify(title: str, message: str) -> None:
    if platform.system() != "Darwin" or not shutil.which("osascript"):
        return
    safe = _applescript_escape(message)
    safe_title = _applescript_escape(title)
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe}" with title "{safe_title}" sound name "Glass"'],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:
        pass


def _ntfy_body(slots: list[Slot], cap: int = 8) -> str:
    """Phone-friendly body: list everything when few; summarize when many."""
    from collections import Counter

    line = lambda s: f"{s.park_name} — {s.date} {s.time_label.strip()} Court {s.court}"
    if len(slots) <= cap:
        return "\n".join(line(s) for s in slots)
    by_park = Counter(s.park_name for s in slots)
    summary = " · ".join(f"{n}× {name}" for name, n in by_park.most_common())
    shown = "\n".join(line(s) for s in slots[:cap])
    return f"{summary}\n\n{shown}\n…and {len(slots) - cap} more"


def _ntfy_request(url: str, slots: list[Slot], grid_url: str = "") -> urllib.request.Request:
    """Build an ntfy.sh publish request: plain-text body + ntfy control headers.

    Tapping the notification opens the earliest slot's reservation page directly.
    A slot can be taken/locked by tap time, so an "Open live grid" action button
    (when ``grid_url`` is given) provides a reliable fallback to the live calendar.
    """
    body = _ntfy_body(slots)
    if grid_url:
        body += "\n\nIf a link says \"not bookable\", it was just taken — open the live grid."
    headers = {
        "Title": f"{len(slots)} tennis court(s) open",  # ASCII only (ntfy header)
        "Tags": "tennis",       # renders a 🎾 emoji in the ntfy app
        "Priority": "high",
        "Click": slots[0].reserve_url(),
    }
    if grid_url:
        headers["Actions"] = f"view, Open live grid, {grid_url}"
    return urllib.request.Request(
        url, data=body.encode("utf-8"), headers=headers, method="POST"
    )


def _generic_webhook_request(url: str, slots: list[Slot]) -> urllib.request.Request:
    payload = json.dumps({
        "event": "new_tennis_slots",
        "count": len(slots),
        "slots": [
            {"date": s.date, "time": s.time_label, "court": s.court,
             "reserve_url": s.reserve_url()}
            for s in slots
        ],
    }).encode("utf-8")
    return urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )


def _webhook_notify(url: str, slots: list[Slot], grid_url: str = "") -> None:
    if not url:
        return
    is_ntfy = "ntfy.sh/" in url or "/ntfy/" in url
    req = _ntfy_request(url, slots, grid_url) if is_ntfy else _generic_webhook_request(url, slots)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception:
        pass


def notify_new_slots(slots, webhook_url: str = "", grid_url: str = "") -> None:
    """Announce newly-available matching slots across all configured channels."""
    slots = list(slots)  # snapshot: tolerate a one-shot iterator
    if not slots:
        return
    title = f"🎾 {len(slots)} tennis slot(s) open"
    body = format_slots(slots)
    print("\n" + "=" * 52)
    print(title)
    print(body)
    print("Book at: " + slots[0].reserve_url())
    if grid_url:
        print("Live grid (if a link is dead): " + grid_url)
    print("=" * 52 + "\n", flush=True)
    _macos_notify(title, f"{len(slots)} new slot(s). Earliest: {slots[0]}")
    _webhook_notify(webhook_url, slots, grid_url)
