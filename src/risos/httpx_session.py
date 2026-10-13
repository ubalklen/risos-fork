from __future__ import annotations

import logging

import httpx

from risos.models import BrowserConfig, SourceConfig

logger = logging.getLogger(__name__)


def fetch_with_browser_session(source: SourceConfig, settings: BrowserConfig) -> str:
    try:
        from patchright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("Session validation requires 'uv sync --extra browser'") from error

    cookies = httpx.Cookies()
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_dir),
            channel="chrome",
            headless=settings.headless,
            no_viewport=True,
            timeout=settings.timeout_ms,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            logger.info("Validating browser session before the HTTPX request")
            response = page.goto(
                source.url, wait_until="domcontentloaded", timeout=settings.timeout_ms
            )
            logger.info(
                "Browser validation initial status: %s", response.status if response else None
            )
            page.locator(settings.wait_for).first.wait_for(
                state="attached", timeout=settings.timeout_ms
            )
            user_agent = page.evaluate("() => navigator.userAgent")
            for cookie in context.cookies([source.url]):
                if cookie["name"] == "cf_clearance":
                    cookies.set(
                        cookie["name"],
                        cookie["value"],
                        domain=cookie["domain"],
                        path=cookie["path"],
                    )
            if not cookies:
                raise RuntimeError("The dedicated browser session has no verification cookie")
        finally:
            context.close()

    logger.info("Browser session validated; fetching the page with HTTPX")
    headers = dict(source.headers)
    headers["User-Agent"] = user_agent
    with httpx.Client(
        follow_redirects=True, timeout=30.0, trust_env=False, headers=headers, cookies=cookies
    ) as client:
        response = client.get(source.url)
        logger.info("HTTPX status: %d (%s)", response.status_code, response.http_version)
        response.raise_for_status()
        return response.text
