from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class FeedMeta(BaseModel):
    title: str
    link: str
    description: str
    language: str = "en"


class SourceConfig(BaseModel):
    url: str
    headers: dict[str, str] = {}


class Transform(BaseModel):
    type: Literal[
        "regex",
        "replace",
        "strip",
        "strip_html",
        "date_parse",
        "absolute_url",
        "truncate",
        "template",
        "split",
        "join",
    ]
    pattern: str | None = None
    group: int = 1
    old: str | None = None
    new: str | None = None
    format: str | None = None
    locale: str | None = None
    base_url: str | None = None
    max_length: int | None = None
    separator: str | None = None
    index: int | None = None

    @model_validator(mode="after")
    def check_required_fields(self) -> Transform:
        rules: dict[str, list[str]] = {
            "regex": ["pattern"],
            "replace": ["old", "new"],
            "absolute_url": ["base_url"],
            "truncate": ["max_length"],
            "template": ["pattern"],
            "split": ["separator", "index"],
        }
        required = rules.get(self.type, [])
        for field in required:
            if getattr(self, field) is None:
                raise ValueError(f"Transform '{self.type}' requires '{field}'")
        return self


class FieldSelector(BaseModel):
    css: str | None = None
    xpath: str | None = None
    attribute: str = "text"
    multiple: bool = False
    default: str | None = None
    transforms: list[Transform] = []

    @model_validator(mode="after")
    def check_exactly_one_selector(self) -> FieldSelector:
        if self.css and self.xpath:
            raise ValueError("Specify exactly one of 'css' or 'xpath', not both")
        if not self.css and not self.xpath:
            raise ValueError("Specify exactly one of 'css' or 'xpath'")
        return self


class ItemListSelector(FieldSelector):
    include_siblings: int = 0


class SelectorsConfig(BaseModel):
    item_list: ItemListSelector
    fields: dict[str, FieldSelector]

    @model_validator(mode="after")
    def check_required_fields(self) -> SelectorsConfig:
        if "title" not in self.fields and "description" not in self.fields:
            raise ValueError("'fields' must contain at least 'title' or 'description'")
        return self


class SiteConfig(BaseModel):
    feed: FeedMeta
    source: SourceConfig
    selectors: SelectorsConfig
