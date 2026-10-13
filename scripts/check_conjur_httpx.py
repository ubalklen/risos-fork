from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from risos.generator import build_feed, write_feeds
from risos.httpx_session import fetch_with_browser_session
from risos.models import BrowserConfig, SiteConfig
from risos.scraper import extract_items, fetch_page


def main() -> int:
    parser = argparse.ArgumentParser(description="Test ConJur access through HTTPX")
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--browser-session",
        action="store_true",
        help="Validate the dedicated Chrome session before the HTTPX request",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Write RSS and Atom after finding articles"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        config = SiteConfig(**yaml.safe_load(args.config.read_text(encoding="utf-8")))
        item_selector = config.selectors.item_list
        selector = item_selector.css or f"xpath={item_selector.xpath}"
        if args.browser_session:
            settings = config.source.browser or BrowserConfig(wait_for=selector)
            html = fetch_with_browser_session(config.source, settings)
        else:
            html = fetch_page(config.source.model_copy(update={"browser": None}))
        items = extract_items(html, config.selectors)
        if not items:
            raise RuntimeError("HTTPX did not receive any feed articles")
        print(f"HTTPX received {len(items)} feed articles")
        if args.output_dir is not None:
            write_feeds(build_feed(config.feed, items), args.output_dir, args.config.stem)
        return 0
    except Exception as error:
        print(f"HTTPX test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
