"""
Shared HTTP client with automatic retry and backoff.

Provides a pre-configured ``requests.Session`` that retries on transient
network errors (timeouts, connection resets, 502/503/504) with exponential
backoff.  All service modules should use this instead of bare ``requests.get``.

Usage::

    from butterfly_planner.services.http import session

    resp = session.get("https://api.example.com/v1/data", timeout=30)
    resp.raise_for_status()
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

#: Default retry strategy — handles the transient errors we see in practice.
DEFAULT_RETRY = Retry(
    total=4,
    backoff_factor=2,  # 0s, 2s, 4s, 8s between retries
    status_forcelist=[429, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS"],
    raise_on_status=False,  # let resp.raise_for_status() handle it
)

DEFAULT_TIMEOUT = 30  # seconds


def create_session(
    retry: Retry | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> requests.Session:
    """
    Build a ``requests.Session`` with retry adapter mounted.

    Args:
        retry: Custom retry strategy (defaults to ``DEFAULT_RETRY``).
        timeout: Default timeout applied to every request.
    """
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=retry or DEFAULT_RETRY)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers["User-Agent"] = "butterfly-planner/0.1 (https://github.com/mihow/butterfly-planner)"

    # Monkey-patch send to inject a default timeout so callers don't need to
    # remember to pass ``timeout=`` every time.
    _original_send = s.send

    def _send_with_timeout(
        prepared: requests.PreparedRequest, **kwargs: object
    ) -> requests.Response:
        kwargs.setdefault("timeout", timeout)
        return _original_send(prepared, **kwargs)  # type: ignore[arg-type]

    s.send = _send_with_timeout  # type: ignore[method-assign]
    return s


#: Module-level session — import and use directly.
session: requests.Session = create_session()
