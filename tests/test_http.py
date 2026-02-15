"""Tests for the shared HTTP client with retry logic."""

from __future__ import annotations

from unittest.mock import patch

import requests
from urllib3.util.retry import Retry

from butterfly_planner.services.http import DEFAULT_RETRY, DEFAULT_TIMEOUT, create_session, session


class TestDefaultRetry:
    """Verify retry strategy configuration."""

    def test_total_retries(self) -> None:
        assert DEFAULT_RETRY.total == 4

    def test_backoff_factor(self) -> None:
        assert DEFAULT_RETRY.backoff_factor == 2

    def test_retries_on_server_errors(self) -> None:
        assert 502 in DEFAULT_RETRY.status_forcelist
        assert 503 in DEFAULT_RETRY.status_forcelist
        assert 504 in DEFAULT_RETRY.status_forcelist

    def test_retries_on_rate_limit(self) -> None:
        assert 429 in DEFAULT_RETRY.status_forcelist

    def test_only_safe_methods(self) -> None:
        allowed = DEFAULT_RETRY.allowed_methods
        assert "GET" in allowed
        assert "POST" not in allowed


class TestCreateSession:
    """Verify session factory."""

    def test_returns_session(self) -> None:
        s = create_session()
        assert isinstance(s, requests.Session)

    def test_mounts_https_adapter(self) -> None:
        s = create_session()
        adapter = s.get_adapter("https://example.com")
        assert isinstance(adapter, requests.adapters.HTTPAdapter)

    def test_mounts_http_adapter(self) -> None:
        s = create_session()
        adapter = s.get_adapter("http://example.com")
        assert isinstance(adapter, requests.adapters.HTTPAdapter)

    def test_adapter_has_retry(self) -> None:
        s = create_session()
        adapter = s.get_adapter("https://example.com")
        assert adapter.max_retries.total == 4

    def test_custom_retry(self) -> None:
        custom = Retry(total=10, backoff_factor=1)
        s = create_session(retry=custom)
        adapter = s.get_adapter("https://example.com")
        assert adapter.max_retries.total == 10

    def test_user_agent_header(self) -> None:
        s = create_session()
        assert "butterfly-planner" in s.headers["User-Agent"]

    def test_default_timeout_injected(self) -> None:
        s = create_session(timeout=42)
        prep = requests.Request("GET", "https://example.com").prepare()
        # Patch the bound method captured by the closure
        with patch.object(
            requests.adapters.HTTPAdapter, "send", return_value=requests.Response()
        ) as mock_send:
            s.send(prep)
            _, kwargs = mock_send.call_args
            assert kwargs.get("timeout") == 42

    def test_explicit_timeout_not_overridden(self) -> None:
        s = create_session(timeout=42)
        prep = requests.Request("GET", "https://example.com").prepare()
        with patch.object(
            requests.adapters.HTTPAdapter, "send", return_value=requests.Response()
        ) as mock_send:
            s.send(prep, timeout=99)
            _, kwargs = mock_send.call_args
            assert kwargs.get("timeout") == 99


class TestModuleSession:
    """Verify the module-level singleton."""

    def test_session_is_configured(self) -> None:
        adapter = session.get_adapter("https://example.com")
        assert adapter.max_retries.total == 4

    def test_default_timeout(self) -> None:
        assert DEFAULT_TIMEOUT == 30
