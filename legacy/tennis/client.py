"""HTTP client for the NYC Parks tennis reservation site.

The site rejects non-browser user agents (plain requests get HTTP 403), so we
send a realistic browser ``User-Agent`` and ``Accept`` headers. Stdlib only.

Read paths (availability, reserve form) are GET and safe to call freely. The
write path (:meth:`submit_registration`) is only invoked by the opt-in booking
flow and stops *before* payment.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class FetchError(RuntimeError):
    """Raised when a request fails after exhausting retries."""


def looks_like_availability(html: str) -> bool:
    """Heuristic: does this page actually look like an availability calendar?

    Guards against a bot-detection / CAPTCHA / challenge interstitial that the
    site might serve with HTTP 200 — which would otherwise parse to zero slots
    and be indistinguishable from "nothing available".
    """
    return 'class="tab-pane' in html and ">Court " in html


class TennisClient:
    def __init__(
        self,
        base_url: str = "https://www.nycgovparks.org",
        timeout: int = 20,
        max_retries: int = 3,
        backoff_seconds: float = 5.0,
        sleep=time.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._sleep = sleep

    # -- internal ----------------------------------------------------------

    def _request(self, method: str, path: str, data: bytes | None = None) -> str:
        url = path if path.startswith("http") else self.base_url + path
        headers = dict(BROWSER_HEADERS)
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Referer"] = self.base_url + "/tennisreservation"
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as exc:
                last_err = exc
                # Permanent client errors (e.g. 403/404) won't fix themselves;
                # fail fast instead of burning the retry budget every cycle.
                if 400 <= exc.code < 500 and exc.code != 429:
                    raise FetchError(f"{method} {url} -> HTTP {exc.code} {exc.reason}") from exc
                if attempt < self.max_retries:
                    self._sleep(self.backoff_seconds * attempt)
            except (urllib.error.URLError, TimeoutError) as exc:
                last_err = exc
                if attempt < self.max_retries:
                    self._sleep(self.backoff_seconds * attempt)
        raise FetchError(f"{method} {url} failed after {self.max_retries} tries: {last_err}")

    # -- read (safe) -------------------------------------------------------

    def fetch_availability(self, park_id: int) -> str:
        """GET the full 30-day availability page for a park.

        Raises :class:`FetchError` if the response doesn't look like a real
        availability page (e.g. a block/challenge interstitial served as 200),
        so callers back off instead of silently reporting "no slots".
        """
        html = self._request("GET", f"/tennisreservation/availability/{park_id}")
        if not looks_like_availability(html):
            raise FetchError(
                "availability page missing expected content "
                "(possible block / challenge page, or site layout change)"
            )
        return html

    def fetch_reserve_form(self, reserve_path: str) -> str:
        """GET the booking form for a slot (``reserve_path`` is the full href)."""
        return self._request("GET", reserve_path)

    def check_bookable(self, reserve_path: str) -> str:
        """Best-effort: is this slot *actually* bookable right now?

        The availability grid marks slots ``status2`` ("Reserve this time"), but
        that doesn't guarantee the reserve step accepts them — some are taken,
        transiently locked, or persistent grid false-positives. This GETs the
        reserve page (``reserve_path`` is the slot's full href, ``reserve`` or
        ``reservecp``) and classifies the result. A GET does not appear to lock
        the slot (a known-good slot stays bookable across repeated GETs).

        Returns ``"bookable"``, ``"taken"`` (site says "not bookable"), or
        ``"unknown"`` (throttled / network / unexpected — caller should not
        suppress the slot on uncertainty).
        """
        try:
            html = self._request("GET", reserve_path)
        except FetchError:
            return "unknown"
        low = html.lower()
        if "not bookable" in low:
            return "taken"
        if "continue to payment" in low or "player details" in low:
            return "bookable"
        return "unknown"

    # -- write (opt-in; pre-payment only) ----------------------------------

    def submit_registration(self, payload: dict) -> str:
        """POST applicant details to ``registercp``.

        This advances to the *payment* page; it does NOT charge anything. Only
        the opt-in booking flow calls this, and only with explicit confirmation.
        """
        body = urllib.parse.urlencode(payload).encode("utf-8")
        return self._request("POST", "/tennisreservation/registercp", data=body)
