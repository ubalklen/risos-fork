from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup, Tag
from lxml import html as lxml_html

from risos.models import SelectorsConfig, SourceConfig
from risos.transforms import apply_transforms

logger = logging.getLogger(__name__)


def fetch_page(source: SourceConfig) -> str:
    logger.info("Fetching %s", source.url)
    with httpx.Client(follow_redirects=True, timeout=30.0, trust_env=False) as client:
        resp = client.get(source.url, headers=source.headers)
        resp.raise_for_status()
    logger.info("Fetched %s — %d bytes", source.url, len(resp.text))
    return resp.text


def _select_elements(container: Tag, css: str | None, xpath: str | None) -> list[Tag]:
    if css:
        return container.select(css)
    if xpath:
        tree = lxml_html.fromstring(str(container))
        lxml_results = tree.xpath(xpath)
        results: list[Tag] = []
        for el in lxml_results:
            text = lxml_html.tostring(el, encoding="unicode")
            parsed = BeautifulSoup(text, "html.parser")
            tag = parsed.find()
            if tag and isinstance(tag, Tag):
                results.append(tag)
        return results
    return []


def _extract_value(element: Tag, attribute: str) -> str | None:
    if attribute == "text":
        return element.get_text(strip=True) or None
    val = element.get(attribute)
    if isinstance(val, list):
        return " ".join(val)
    return val


def extract_items(html: str, selectors: SelectorsConfig) -> list[dict[str, str | None]]:
    soup = BeautifulSoup(html, "lxml")
    il = selectors.item_list
    items_elements = _select_elements(soup, il.css, il.xpath)
    logger.info("Found %d item elements", len(items_elements))

    results: list[dict[str, str | None]] = []
    for elem in items_elements:
        container: Tag
        if il.include_siblings > 0:
            siblings = []
            current = elem
            for _ in range(il.include_siblings):
                ns = current.find_next_sibling()
                if ns and isinstance(ns, Tag):
                    siblings.append(ns)
                    current = ns
                else:
                    break
            wrapper = BeautifulSoup("<div></div>", "html.parser").find("div")
            assert isinstance(wrapper, Tag)
            from copy import copy

            wrapper.append(copy(elem))
            for sib in siblings:
                wrapper.append(copy(sib))
            container = wrapper
        else:
            container = elem

        item: dict[str, str | None] = {}
        for field_name, field_sel in selectors.fields.items():
            matches = _select_elements(container, field_sel.css, field_sel.xpath)

            if field_sel.multiple and matches:
                values = []
                for m in matches:
                    v = _extract_value(m, field_sel.attribute)
                    if v:
                        values.append(v)
                raw_value: str | None = ", ".join(values) if values else None
            elif matches:
                raw_value = _extract_value(matches[0], field_sel.attribute)
            else:
                raw_value = None

            if raw_value is None and field_sel.default is not None:
                raw_value = field_sel.default

            if raw_value is not None and field_sel.transforms:
                raw_value = apply_transforms(raw_value, field_sel.transforms)

            item[field_name] = raw_value

        if item.get("title") is None and item.get("description") is None:
            logger.debug("Skipping item with no title and no description")
            continue

        results.append(item)

    logger.info("Extracted %d items", len(results))
    return results
