from __future__ import annotations

import pytest
import yaml

from risos.models import (
    FieldSelector,
    ItemListSelector,
    SelectorsConfig,
    SiteConfig,
    Transform,
)

VALID_YAML = """
feed:
  title: "Test"
  link: "https://example.com"
  description: "Test feed"
source:
  url: "https://example.com"
selectors:
  item_list:
    css: "div.item"
  fields:
    title:
      css: "h1"
"""


def test_valid_yaml_parses():
    data = yaml.safe_load(VALID_YAML)
    config = SiteConfig(**data)
    assert config.feed.title == "Test"
    assert config.source.url == "https://example.com"
    assert "title" in config.selectors.fields


def test_rejects_css_and_xpath():
    with pytest.raises(ValueError, match="exactly one"):
        FieldSelector(css="div", xpath="//div")


def test_rejects_no_selector():
    with pytest.raises(ValueError, match="exactly one"):
        FieldSelector()


def test_rejects_fields_without_title_or_description():
    with pytest.raises(ValueError, match="title.*description|description.*title"):
        SelectorsConfig(
            item_list=ItemListSelector(css="div"),
            fields={"link": FieldSelector(css="a")},
        )


def test_transform_regex_requires_pattern():
    with pytest.raises(ValueError, match="requires 'pattern'"):
        Transform(type="regex")


def test_transform_replace_requires_old_new():
    with pytest.raises(ValueError, match="requires 'old'"):
        Transform(type="replace", new="x")
    with pytest.raises(ValueError, match="requires 'new'"):
        Transform(type="replace", old="x")


def test_transform_absolute_url_requires_base_url():
    with pytest.raises(ValueError, match="requires 'base_url'"):
        Transform(type="absolute_url")


def test_transform_truncate_requires_max_length():
    with pytest.raises(ValueError, match="requires 'max_length'"):
        Transform(type="truncate")


def test_transform_template_requires_pattern():
    with pytest.raises(ValueError, match="requires 'pattern'"):
        Transform(type="template")


def test_transform_split_requires_separator_index():
    with pytest.raises(ValueError, match="requires 'separator'"):
        Transform(type="split", index=0)
    with pytest.raises(ValueError, match="requires 'index'"):
        Transform(type="split", separator=",")


def test_include_siblings_default():
    sel = ItemListSelector(css="div")
    assert sel.include_siblings == 0


def test_field_selector_defaults():
    sel = FieldSelector(css="div")
    assert sel.attribute == "text"
    assert sel.multiple is False
    assert sel.default is None
    assert sel.transforms == []


def test_source_config_default_headers():
    from risos.models import SourceConfig

    sc = SourceConfig(url="https://example.com")
    assert sc.headers == {}


def test_hacker_news_yaml(hacker_news_config):
    assert hacker_news_config.feed.title == "Hacker News"
    assert hacker_news_config.selectors.item_list.include_siblings == 1
    assert "title" in hacker_news_config.selectors.fields
    assert "author" in hacker_news_config.selectors.fields


def test_transform_strip_no_extra_fields():
    t = Transform(type="strip")
    assert t.pattern is None


def test_transform_date_parse_optional_fields():
    t = Transform(type="date_parse")
    assert t.format is None
    assert t.locale is None


def test_feed_meta_language_default():
    from risos.models import FeedMeta

    fm = FeedMeta(title="T", link="https://x.com", description="D")
    assert fm.language == "en"
