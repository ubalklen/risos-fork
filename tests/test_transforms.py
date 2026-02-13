from __future__ import annotations

import logging

from risos.models import Transform
from risos.transforms import apply_transforms


def test_regex_extracts_group():
    t = Transform(type="regex", pattern=r"(\d+) points", group=1)
    assert apply_transforms("42 points", [t]) == "42"


def test_regex_no_match_returns_original():
    t = Transform(type="regex", pattern=r"(\d+) xyz", group=1)
    assert apply_transforms("no match here", [t]) == "no match here"


def test_replace():
    t = Transform(type="replace", old="foo", new="bar")
    assert apply_transforms("foo baz foo", [t]) == "bar baz bar"


def test_strip():
    t = Transform(type="strip")
    assert apply_transforms("  hello  ", [t]) == "hello"


def test_strip_html():
    t = Transform(type="strip_html")
    assert apply_transforms("<b>bold</b> text", [t]) == "bold text"


def test_date_parse_iso():
    t = Transform(type="date_parse")
    result = apply_transforms("2024-01-15T12:00:00Z", [t])
    assert "Mon, 15 Jan 2024" in result


def test_date_parse_custom_format():
    t = Transform(type="date_parse", format="%d/%m/%Y")
    result = apply_transforms("15/01/2024", [t])
    assert "Mon, 15 Jan 2024" in result


def test_date_parse_fallback_heuristic():
    t = Transform(type="date_parse")
    result = apply_transforms("January 15, 2024", [t])
    assert "15 Jan 2024" in result


def test_date_parse_invalid_returns_original(caplog):
    t = Transform(type="date_parse")
    with caplog.at_level(logging.WARNING):
        result = apply_transforms("not-a-date-xyz", [t])
    assert result == "not-a-date-xyz"
    assert "could not parse" in caplog.text.lower()


def test_absolute_url_relative():
    t = Transform(type="absolute_url", base_url="https://example.com/page/")
    assert apply_transforms("/foo/bar", [t]) == "https://example.com/foo/bar"


def test_absolute_url_already_absolute():
    t = Transform(type="absolute_url", base_url="https://example.com")
    assert apply_transforms("https://other.com/x", [t]) == "https://other.com/x"


def test_truncate_long():
    t = Transform(type="truncate", max_length=5)
    assert apply_transforms("abcdefgh", [t]) == "abcde\u2026"


def test_truncate_short():
    t = Transform(type="truncate", max_length=100)
    assert apply_transforms("short", [t]) == "short"


def test_template():
    t = Transform(type="template", pattern="<a>{value}</a>")
    assert apply_transforms("hello", [t]) == "<a>hello</a>"


def test_split():
    t = Transform(type="split", separator=",", index=1)
    assert apply_transforms("a,b,c", [t]) == "b"


def test_split_out_of_range():
    t = Transform(type="split", separator=",", index=10)
    assert apply_transforms("a,b", [t]) == "a,b"


def test_join_list():
    from risos.transforms import _join

    t = Transform(type="strip")
    result = _join(["a", "b", "c"], t)
    assert result == "a, b, c"


def test_pipeline_regex_then_date_parse():
    transforms = [
        Transform(type="regex", pattern=r"^(\S+)"),
        Transform(type="date_parse"),
    ]
    result = apply_transforms("2024-06-15T10:30:00 extra", transforms)
    assert "Sat, 15 Jun 2024" in result


def test_failed_transform_returns_original(caplog):
    t = Transform(type="split", separator=",", index=0)
    with caplog.at_level(logging.WARNING):
        result = apply_transforms(None, [t])
    assert result is None
