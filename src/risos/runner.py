from __future__ import annotations

import logging
from pathlib import Path

import yaml

from risos.generator import build_feed, write_feeds
from risos.models import SiteConfig
from risos.scraper import extract_items, fetch_page

logger = logging.getLogger(__name__)


def load_sites(sites_dir: Path) -> list[tuple[str, SiteConfig]]:
    configs: list[tuple[str, SiteConfig]] = []
    if not sites_dir.is_dir():
        logger.error("Sites directory %s does not exist", sites_dir)
        return configs
    for yaml_file in sorted(sites_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            config = SiteConfig(**data)
            configs.append((yaml_file.stem, config))
            logger.info("Loaded site config: %s", yaml_file.stem)
        except Exception:
            logger.error("Failed to load %s", yaml_file, exc_info=True)
    return configs


def run_one(site_path: Path, output_dir: Path) -> None:
    data = yaml.safe_load(site_path.read_text(encoding="utf-8"))
    config = SiteConfig(**data)
    name = site_path.stem

    html = fetch_page(config.source)
    items = extract_items(html, config.selectors)
    logger.info("Site '%s': extracted %d items", name, len(items))
    fg = build_feed(config.feed, items)
    write_feeds(fg, output_dir, name)


def run_all(sites_dir: Path, output_dir: Path) -> None:
    sites = load_sites(sites_dir)
    if not sites:
        logger.warning("No site configs found in %s", sites_dir)
        return

    for name, config in sites:
        try:
            html = fetch_page(config.source)
            items = extract_items(html, config.selectors)
            logger.info("Site '%s': extracted %d items", name, len(items))
            fg = build_feed(config.feed, items)
            write_feeds(fg, output_dir, name)
        except Exception:
            logger.error("Failed to process site '%s'", name, exc_info=True)

    _generate_index(output_dir, [name for name, _ in sites])


def _generate_index(output_dir: Path, site_names: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    items_html = ""
    for name in site_names:
        items_html += (
            f"  <li><strong>{name}</strong> — "
            f'<a href="{name}.rss.xml">RSS</a> | '
            f'<a href="{name}.atom.xml">Atom</a></li>\n'
        )
    html = (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset='utf-8'><title>risos feeds</title></head>\n"
        "<body>\n<h1>risos — RSS/Atom Feeds</h1>\n<ul>\n"
        f"{items_html}</ul>\n</body></html>\n"
    )
    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    logger.info("Wrote %s", index_path)
