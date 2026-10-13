from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
import yaml

from risos.models import BrowserConfig, SiteConfig, SourceConfig
from risos.scraper import extract_items, fetch_page


@pytest.fixture
def browser_runtime(monkeypatch, tmp_path):
    factory = MagicMock()
    monkeypatch.setitem(
        sys.modules, "patchright.sync_api", SimpleNamespace(sync_playwright=factory)
    )
    playwright = factory.return_value.__enter__.return_value
    context = playwright.chromium.launch_persistent_context.return_value
    context.pages = []
    page = context.new_page.return_value
    page.goto.return_value.status = 403
    page.content.return_value = '<html><div class="item">Article</div></html>'
    source = SourceConfig(
        url="https://example.com",
        headers={"User-Agent": "risos/1.0"},
        browser=BrowserConfig(wait_for=".item", profile_dir=tmp_path / "chrome-profile"),
    )
    return source, playwright, context, page


def test_fetch_browser_waits_for_articles_after_initial_403(browser_runtime, httpx_mock):
    source, playwright, context, page = browser_runtime

    assert "Article" in fetch_page(source)

    playwright.chromium.launch_persistent_context.assert_called_once_with(
        user_data_dir=str(source.browser.profile_dir),
        channel="chrome",
        headless=False,
        no_viewport=True,
        timeout=90_000,
    )
    page.goto.assert_called_once_with(source.url, wait_until="domcontentloaded", timeout=90_000)
    page.locator.assert_called_once_with(".item")
    page.locator.return_value.first.wait_for.assert_called_once_with(
        state="attached", timeout=90_000
    )
    context.close.assert_called_once_with()
    assert httpx_mock.get_requests() == []


def test_fetch_browser_closes_context_on_wait_failure(browser_runtime):
    source, _, context, page = browser_runtime
    page.locator.return_value.first.wait_for.side_effect = TimeoutError("Challenge unresolved")

    with pytest.raises(TimeoutError, match="Challenge unresolved"):
        fetch_page(source)

    page.content.assert_not_called()
    context.close.assert_called_once_with()


def test_fetch_browser_closes_context_on_navigation_failure(browser_runtime):
    source, _, context, page = browser_runtime
    page.goto.side_effect = RuntimeError("Navigation failed")

    with pytest.raises(RuntimeError, match="Navigation failed"):
        fetch_page(source)

    context.close.assert_called_once_with()


def test_fetch_browser_reuses_initial_page(browser_runtime):
    source, _, context, page = browser_runtime
    context.pages = [page]

    assert "Article" in fetch_page(source)

    context.new_page.assert_not_called()
    context.close.assert_called_once_with()


def test_fetch_browser_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "patchright.sync_api", None)
    source = SourceConfig(url="https://example.com", browser=BrowserConfig(wait_for=".item"))

    with pytest.raises(RuntimeError, match="uv sync --extra browser"):
        fetch_page(source)


def test_fetch_page_success(httpx_mock):
    httpx_mock.add_response(url="https://example.com", text="<html>ok</html>")
    from risos.models import SourceConfig

    result = fetch_page(SourceConfig(url="https://example.com", headers={"X-Test": "1"}))
    assert "ok" in result
    req = httpx_mock.get_request()
    assert req.headers["X-Test"] == "1"


def test_fetch_page_error(httpx_mock):
    httpx_mock.add_response(url="https://example.com", status_code=500)
    from risos.models import SourceConfig

    with pytest.raises(httpx.HTTPStatusError):
        fetch_page(SourceConfig(url="https://example.com"))


def test_extract_items_hacker_news(hacker_news_html, hacker_news_config):
    items = extract_items(hacker_news_html, hacker_news_config.selectors)
    assert len(items) >= 20
    for item in items:
        assert item.get("title") is not None
        assert item.get("link") is not None


def test_include_siblings_accesses_sibling_fields(hacker_news_html, hacker_news_config):
    items = extract_items(hacker_news_html, hacker_news_config.selectors)
    has_author = any(item.get("author") and item["author"] != "unknown" for item in items)
    assert has_author, "At least one item should have a real author from sibling row"


def test_field_default_value():
    html = """
    <html><body>
    <div class="item"><h1>Title</h1></div>
    </body></html>
    """
    config_yaml = """
    feed:
      title: Test
      link: https://example.com
      description: Test
    source:
      url: https://example.com
    selectors:
      item_list:
        css: "div.item"
      fields:
        title:
          css: "h1"
        description:
          css: ".missing"
          default: "no description"
    """
    config = SiteConfig(**yaml.safe_load(config_yaml))
    items = extract_items(html, config.selectors)
    assert len(items) == 1
    assert items[0]["description"] == "no description"


def test_xpath_selector():
    html = """
    <html><body>
    <div class="item"><span class="t">XPath Title</span></div>
    </body></html>
    """
    config_yaml = """
    feed:
      title: Test
      link: https://example.com
      description: Test
    source:
      url: https://example.com
    selectors:
      item_list:
        xpath: "//div[@class='item']"
      fields:
        title:
          xpath: ".//span[@class='t']"
    """
    config = SiteConfig(**yaml.safe_load(config_yaml))
    items = extract_items(html, config.selectors)
    assert len(items) == 1
    assert items[0]["title"] == "XPath Title"


def test_skip_items_without_title_or_description():
    html = """
    <html><body>
    <div class="item"><span class="other">nope</span></div>
    </body></html>
    """
    config_yaml = """
    feed:
      title: Test
      link: https://example.com
      description: Test
    source:
      url: https://example.com
    selectors:
      item_list:
        css: "div.item"
      fields:
        title:
          css: ".title"
        description:
          css: ".desc"
    """
    config = SiteConfig(**yaml.safe_load(config_yaml))
    items = extract_items(html, config.selectors)
    assert len(items) == 0


def test_multiple_attribute():
    html = """
    <html><body>
    <div class="item">
      <span class="tag">a</span>
      <span class="tag">b</span>
      <span class="tag">c</span>
    </div>
    </body></html>
    """
    config_yaml = """
    feed:
      title: Test
      link: https://example.com
      description: Test
    source:
      url: https://example.com
    selectors:
      item_list:
        css: "div.item"
      fields:
        title:
          css: ".tag"
          multiple: true
    """
    config = SiteConfig(**yaml.safe_load(config_yaml))
    items = extract_items(html, config.selectors)
    assert len(items) == 1
    assert items[0]["title"] == "a, b, c"


def test_extract_attribute():
    html = """
    <html><body>
    <div class="item"><a href="https://example.com">Link</a></div>
    </body></html>
    """
    config_yaml = """
    feed:
      title: Test
      link: https://example.com
      description: Test
    source:
      url: https://example.com
    selectors:
      item_list:
        css: "div.item"
      fields:
        title:
          css: "a"
          attribute: "href"
    """
    config = SiteConfig(**yaml.safe_load(config_yaml))
    items = extract_items(html, config.selectors)
    assert len(items) == 1
    assert items[0]["title"] == "https://example.com"
