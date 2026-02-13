from __future__ import annotations

import logging
import re
import urllib.parse
from collections.abc import Callable
from email.utils import format_datetime

from babel.dates import parse_date
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from risos.models import Transform

logger = logging.getLogger(__name__)


def _regex(value: str, t: Transform) -> str:
    assert t.pattern is not None
    m = re.search(t.pattern, value)
    if m:
        return m.group(t.group)
    logger.warning("regex pattern %r did not match value %r", t.pattern, value)
    return value


def _replace(value: str, t: Transform) -> str:
    assert t.old is not None and t.new is not None
    return value.replace(t.old, t.new)


def _strip(value: str, _t: Transform) -> str:
    return value.strip()


def _strip_html(value: str, _t: Transform) -> str:
    return BeautifulSoup(value, "html.parser").get_text()


def _date_parse(value: str, t: Transform) -> str:
    import contextlib
    from datetime import UTC, datetime

    dt: datetime | None = None
    if t.locale:
        with contextlib.suppress(Exception):
            d = parse_date(value, locale=t.locale)
            dt = datetime(d.year, d.month, d.day, tzinfo=UTC)
    if dt is None and t.format:
        with contextlib.suppress(Exception):
            dt = datetime.strptime(value, t.format).replace(tzinfo=UTC)
    if dt is None:
        with contextlib.suppress(Exception):
            dt = dateutil_parser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
    if dt is None:
        logger.warning("date_parse could not parse value %r", value)
        return value
    return format_datetime(dt)


def _absolute_url(value: str, t: Transform) -> str:
    assert t.base_url is not None
    return urllib.parse.urljoin(t.base_url, value)


def _truncate(value: str, t: Transform) -> str:
    assert t.max_length is not None
    if len(value) > t.max_length:
        return value[: t.max_length] + "\u2026"
    return value


def _template(value: str, t: Transform) -> str:
    assert t.pattern is not None
    return t.pattern.replace("{value}", value)


def _split(value: str, t: Transform) -> str:
    assert t.separator is not None and t.index is not None
    parts = value.split(t.separator)
    if t.index < len(parts):
        return parts[t.index]
    return value


def _join(value: str, t: Transform) -> str:
    sep = t.separator if t.separator is not None else ", "
    return sep.join(value) if isinstance(value, list) else value


TRANSFORMS: dict[str, Callable[[str, Transform], str]] = {
    "regex": _regex,
    "replace": _replace,
    "strip": _strip,
    "strip_html": _strip_html,
    "date_parse": _date_parse,
    "absolute_url": _absolute_url,
    "truncate": _truncate,
    "template": _template,
    "split": _split,
    "join": _join,
}


def apply_transforms(value: str, transforms: list[Transform]) -> str:
    for t in transforms:
        fn = TRANSFORMS.get(t.type)
        if fn is None:
            logger.warning("Unknown transform type %r", t.type)
            continue
        try:
            value = fn(value, t)
        except Exception:
            logger.warning(
                "Transform '%s' failed on value %r",
                t.type,
                value,
                exc_info=True,
            )
    return value
