from __future__ import annotations

from lxml import etree

from risos.generator import build_feed, write_feeds
from risos.models import FeedMeta


def _make_items():
    return [
        {
            "title": "Test Title",
            "link": "https://example.com/1",
            "description": "Desc 1",
            "author": "Author1",
            "pubDate": "Mon, 15 Jan 2024 12:00:00 +0000",
        },
        {
            "title": "Title 2",
            "link": "https://example.com/2",
            "description": "Desc 2",
        },
    ]


def _make_meta():
    return FeedMeta(
        title="Test Feed",
        link="https://example.com",
        description="A test feed",
    )


def test_build_feed_rss_valid():
    fg = build_feed(_make_meta(), _make_items())
    xml = fg.rss_str(pretty=True)
    tree = etree.fromstring(xml)
    assert tree.tag == "rss"
    assert tree.get("version") == "2.0"
    channel = tree.find("channel")
    assert channel is not None
    assert channel.find("title").text == "Test Feed"
    items = channel.findall("item")
    assert len(items) == 2


def test_build_feed_atom_valid():
    fg = build_feed(_make_meta(), _make_items())
    xml = fg.atom_str(pretty=True)
    tree = etree.fromstring(xml)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    assert tree.tag == f"{{{ns['atom']}}}feed"
    entries = tree.findall("atom:entry", ns)
    assert len(entries) == 2


def test_items_without_title_and_description_omitted():
    items = [
        {"title": None, "description": None, "link": "https://x.com"},
        {"title": "Valid", "link": "https://x.com"},
    ]
    fg = build_feed(_make_meta(), items)
    xml = fg.rss_str(pretty=True)
    tree = etree.fromstring(xml)
    channel = tree.find("channel")
    rss_items = channel.findall("item")
    assert len(rss_items) == 1


def test_write_feeds_creates_files(tmp_path):
    fg = build_feed(_make_meta(), _make_items())
    write_feeds(fg, tmp_path, "test")
    assert (tmp_path / "test.rss.xml").exists()
    assert (tmp_path / "test.atom.xml").exists()

    rss_content = (tmp_path / "test.rss.xml").read_text(encoding="utf-8")
    assert "<rss" in rss_content


def test_write_feeds_creates_output_dir(tmp_path):
    out = tmp_path / "sub" / "dir"
    fg = build_feed(_make_meta(), _make_items())
    write_feeds(fg, out, "test")
    assert out.exists()
    assert (out / "test.rss.xml").exists()


def test_entry_with_category():
    items = [{"title": "T", "link": "https://x.com", "category": "tech"}]
    fg = build_feed(_make_meta(), items)
    xml = fg.rss_str(pretty=True)
    tree = etree.fromstring(xml)
    cat = tree.find(".//category")
    assert cat is not None
    assert cat.text == "tech"


def test_entry_uses_link_as_guid_fallback():
    items = [{"title": "T", "link": "https://x.com/1"}]
    fg = build_feed(_make_meta(), items)
    xml = fg.rss_str(pretty=True)
    tree = etree.fromstring(xml)
    guid = tree.find(".//guid")
    assert guid is not None
    assert "x.com" in guid.text
