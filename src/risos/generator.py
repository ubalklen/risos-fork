from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from feedgen.feed import FeedGenerator

from risos.models import FeedMeta

logger = logging.getLogger(__name__)


def build_feed(meta: FeedMeta, items: list[dict[str, str | None]]) -> FeedGenerator:
    fg = FeedGenerator()
    fg.id(meta.link)
    fg.title(meta.title)
    fg.link(href=meta.link, rel="alternate")
    fg.description(meta.description)
    fg.language(meta.language)
    fg.generator("risos")
    fg.lastBuildDate(datetime.now(UTC))

    for item in items:
        if item.get("title") is None and item.get("description") is None:
            continue

        entry = fg.add_entry(order="append")
        guid = item.get("guid") or item.get("link") or item.get("title", "")
        entry.id(guid)

        if item.get("title"):
            entry.title(item["title"])
        if item.get("link"):
            entry.link(href=item["link"])
        if item.get("description"):
            entry.description(item["description"])
        if item.get("pubDate"):
            try:
                from email.utils import parsedate_to_datetime

                dt = parsedate_to_datetime(item["pubDate"])
                entry.pubDate(dt)
            except Exception:
                logger.warning("Could not parse pubDate %r", item["pubDate"])
        if item.get("author"):
            entry.author(name=item["author"])
        if item.get("category"):
            entry.category(term=item["category"])

    logger.info("Built feed '%s' with %d entries", meta.title, len(fg.entry()))
    return fg


def write_feeds(fg: FeedGenerator, output_dir: Path, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rss_path = output_dir / f"{name}.rss.xml"
    atom_path = output_dir / f"{name}.atom.xml"
    fg.rss_file(str(rss_path), pretty=True)
    fg.atom_file(str(atom_path), pretty=True)
    logger.info("Wrote %s and %s", rss_path, atom_path)
