from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from risos.httpx_session import fetch_with_browser_session
from risos.models import BrowserConfig, SourceConfig


@pytest.fixture
def validated_browser(monkeypatch, tmp_path):
    factory = MagicMock()
    monkeypatch.setitem(
        sys.modules, "patchright.sync_api", SimpleNamespace(sync_playwright=factory)
    )
    context = (
        factory.return_value.__enter__.return_value.chromium.launch_persistent_context.return_value
    )
    page = context.new_page.return_value
    context.pages = []
    page.evaluate.return_value = "Test Chrome"
    context.cookies.return_value = [
        {"name": "cf_clearance", "value": "test-clearance", "domain": "example.com", "path": "/"},
        {"name": "login", "value": "not-exported", "domain": "example.com", "path": "/"},
    ]
    source = SourceConfig(url="https://example.com")
    settings = BrowserConfig(wait_for=".item", profile_dir=tmp_path / "profile")
    return source, settings, context, page


def test_httpx_fetch_uses_only_verification_cookie(validated_browser, httpx_mock):
    source, settings, context, page = validated_browser
    httpx_mock.add_response(url=source.url, text='<div class="item">From HTTPX</div>')

    html = fetch_with_browser_session(source, settings)

    assert "From HTTPX" in html
    request = httpx_mock.get_request()
    assert request.headers["User-Agent"] == "Test Chrome"
    assert request.headers["Cookie"] == "cf_clearance=test-clearance"
    context.cookies.assert_called_once_with([source.url])
    context.close.assert_called_once_with()
    page.content.assert_not_called()


def test_session_without_verification_cookie_is_rejected(validated_browser, httpx_mock):
    source, settings, context, _ = validated_browser
    context.cookies.return_value = []

    with pytest.raises(RuntimeError, match="no verification cookie"):
        fetch_with_browser_session(source, settings)

    assert httpx_mock.get_requests() == []
    context.close.assert_called_once_with()


def test_browser_timeout_does_not_issue_httpx_request(validated_browser, httpx_mock):
    source, settings, context, page = validated_browser
    page.locator.return_value.first.wait_for.side_effect = TimeoutError("Verification unresolved")

    with pytest.raises(TimeoutError, match="Verification unresolved"):
        fetch_with_browser_session(source, settings)

    assert httpx_mock.get_requests() == []
    context.close.assert_called_once_with()


def test_httpx_block_is_not_replaced_with_browser_html(validated_browser, httpx_mock):
    source, settings, context, page = validated_browser
    httpx_mock.add_response(url=source.url, status_code=403)

    with pytest.raises(httpx.HTTPStatusError):
        fetch_with_browser_session(source, settings)

    context.close.assert_called_once_with()
    page.content.assert_not_called()


def test_missing_browser_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "patchright.sync_api", None)

    with pytest.raises(RuntimeError, match="uv sync --extra browser"):
        fetch_with_browser_session(
            SourceConfig(url="https://example.com"), BrowserConfig(wait_for=".item")
        )
