from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from risos.models import SiteConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SITES_DIR = Path(__file__).parent.parent / "sites"


@pytest.fixture(autouse=True)
def _clean_proxy_env(monkeypatch):
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(var, raising=False)
        monkeypatch.delenv(var.lower(), raising=False)


@pytest.fixture
def hacker_news_html() -> str:
    return (FIXTURES_DIR / "hacker-news.html").read_text(encoding="utf-8")


@pytest.fixture
def hacker_news_config() -> SiteConfig:
    data = yaml.safe_load((SITES_DIR / "hacker-news.yaml").read_text(encoding="utf-8"))
    return SiteConfig(**data)
