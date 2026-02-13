from __future__ import annotations

import logging
from pathlib import Path

import yaml

from risos.runner import _generate_index, load_sites, run_all, run_one


def _write_valid_yaml(path: Path) -> None:
    data = {
        "feed": {"title": "Test", "link": "https://example.com", "description": "TestFeed"},
        "source": {"url": "https://example.com"},
        "selectors": {
            "item_list": {"css": "div.item"},
            "fields": {"title": {"css": "h1"}},
        },
    }
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_invalid_yaml(path: Path) -> None:
    path.write_text("invalid: [yaml: broken", encoding="utf-8")


def test_load_sites_valid(tmp_path):
    _write_valid_yaml(tmp_path / "site1.yaml")
    sites = load_sites(tmp_path)
    assert len(sites) == 1
    assert sites[0][0] == "site1"


def test_load_sites_skips_invalid(tmp_path, caplog):
    _write_valid_yaml(tmp_path / "good.yaml")
    _write_invalid_yaml(tmp_path / "bad.yaml")
    with caplog.at_level(logging.ERROR):
        sites = load_sites(tmp_path)
    assert len(sites) == 1
    assert sites[0][0] == "good"
    assert "failed to load" in caplog.text.lower()


def test_load_sites_nonexistent(tmp_path, caplog):
    with caplog.at_level(logging.ERROR):
        sites = load_sites(tmp_path / "nonexistent")
    assert len(sites) == 0


def test_run_one_end_to_end(tmp_path, httpx_mock, hacker_news_html):
    sites_dir = tmp_path / "sites"
    sites_dir.mkdir()
    hn_yaml = Path(__file__).parent.parent / "sites" / "hacker-news.yaml"
    (sites_dir / "hn.yaml").write_text(hn_yaml.read_text(encoding="utf-8"), encoding="utf-8")

    httpx_mock.add_response(url="https://news.ycombinator.com", text=hacker_news_html)

    output = tmp_path / "output"
    run_one(sites_dir / "hn.yaml", output)

    assert (output / "hn.rss.xml").exists()
    assert (output / "hn.atom.xml").exists()


def test_run_all_generates_index(tmp_path, httpx_mock):
    html = """
    <html><body>
    <div class="item"><h1>A Title</h1></div>
    </body></html>
    """
    httpx_mock.add_response(text=html)

    sites_dir = tmp_path / "sites"
    sites_dir.mkdir()

    data = {
        "feed": {"title": "S1", "link": "https://example.com", "description": "D"},
        "source": {"url": "https://example.com"},
        "selectors": {
            "item_list": {"css": "div.item"},
            "fields": {"title": {"css": "h1"}},
        },
    }
    (sites_dir / "s1.yaml").write_text(yaml.dump(data), encoding="utf-8")

    output = tmp_path / "output"
    run_all(sites_dir, output)

    assert (output / "index.html").exists()
    index = (output / "index.html").read_text(encoding="utf-8")
    assert "s1" in index
    assert "s1.rss.xml" in index


def test_run_all_no_sites(tmp_path, caplog):
    sites_dir = tmp_path / "empty"
    sites_dir.mkdir()
    output = tmp_path / "output"
    with caplog.at_level(logging.WARNING):
        run_all(sites_dir, output)
    assert "no site configs" in caplog.text.lower()


def test_run_all_handles_fetch_error(tmp_path, httpx_mock, caplog):
    httpx_mock.add_response(status_code=500)

    sites_dir = tmp_path / "sites"
    sites_dir.mkdir()
    _write_valid_yaml(sites_dir / "fail.yaml")

    output = tmp_path / "output"
    with caplog.at_level(logging.ERROR):
        run_all(sites_dir, output)
    assert "failed to process" in caplog.text.lower()


def test_generate_index(tmp_path):
    _generate_index(tmp_path, ["site-a", "site-b"])
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "site-a.rss.xml" in index
    assert "site-b.atom.xml" in index
    assert "<h1>" in index
