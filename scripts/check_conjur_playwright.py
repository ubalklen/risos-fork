from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from risos.models import SiteConfig


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()

    data = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    config = SiteConfig(**data)
    item_list = config.selectors.item_list
    selector = item_list.css or f"xpath={item_list.xpath}"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            response = page.goto(
                config.source.url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            status = response.status if response else None
            print(f"HTTP status: {status}")
            if status is None or status >= 400:
                print(f"Browser navigation failed for {config.source.url}")
                return 1

            items = page.locator(selector)
            try:
                items.first.wait_for(state="attached", timeout=20_000)
            except PlaywrightTimeoutError:
                title = page.title()
                body = page.locator("body").inner_text()[:500]
                print(f"Expected selector not found: {selector}")
                print(f"Page title: {title}")
                print(f"Page text: {body}")
                return 1

            count = items.count()
            print(f"Found {count} items using {selector!r}")
            if count == 0:
                return 1
        finally:
            browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
