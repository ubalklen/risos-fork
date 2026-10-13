from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from patchright.sync_api import TimeoutError as PatchrightTimeoutError
from patchright.sync_api import sync_playwright as patchright_sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright as playwright_sync_playwright

from risos.models import SiteConfig


def check_browser(
    name: str,
    playwright_factory: Callable[[], Any],
    timeout_error: type[Exception],
    url: str,
    selector: str,
    launch_options: dict[str, Any] | None = None,
    persistent_context: bool = False,
    wait_timeout: int = 20_000,
    html_output: Path | None = None,
) -> bool:
    print(f"\n=== {name} ===")
    try:
        with playwright_factory() as playwright:
            session = (
                playwright.chromium.launch_persistent_context(**(launch_options or {}))
                if persistent_context
                else playwright.chromium.launch(**(launch_options or {}))
            )
            try:
                page = (
                    session.pages[0]
                    if persistent_context and session.pages
                    else session.new_page()
                )
                try:
                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=60_000,
                    )
                except Exception as error:
                    print(f"Navigation error: {error}")
                    return False

                status = response.status if response else None
                print(f"HTTP status: {status}")
                if status is None:
                    print(f"Browser navigation failed for {url}")
                    return False

                items = page.locator(selector)
                try:
                    items.first.wait_for(state="attached", timeout=wait_timeout)
                except timeout_error:
                    print(f"Expected selector not found: {selector}")
                    print(f"Final URL: {page.url}")
                    print(f"Page title: {page.title()}")
                    print(f"Page text: {page.locator('body').inner_text()[:500]}")
                    return False

                count = items.count()
                print(f"Found {count} items using {selector!r}")
                if count > 0 and html_output is not None:
                    html_output.parent.mkdir(parents=True, exist_ok=True)
                    html_output.write_text(page.content(), encoding="utf-8")
                    print(f"Saved HTML: {html_output}")
                return count > 0
            finally:
                session.close()
    except Exception as error:
        print(f"{name} error: {error}")
        return False


def macro_browser_options(user_data_dir: str) -> dict[str, Any]:
    chrome_paths = (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    )
    chrome_version = "133.0.0.0"
    for chrome_path in chrome_paths:
        if not chrome_path.is_file():
            continue
        try:
            version = subprocess.check_output(
                [
                    "powershell",
                    "-Command",
                    f'(Get-Item "{chrome_path}").VersionInfo.FileVersion',
                ],
                text=True,
                timeout=5,
            ).strip()
            if re.fullmatch(r"\d+(\.\d+)*", version):
                chrome_version = version
                break
        except Exception:
            continue

    major_version = chrome_version.split(".")[0]
    user_agent = (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome_version} Safari/537.36"
    )
    return {
        "user_data_dir": user_data_dir,
        "headless": False,
        "channel": "chrome",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "pt-BR",
        "timezone_id": "America/Sao_Paulo",
        "user_agent": user_agent,
        "ignore_default_args": ["--enable-automation"],
        "extra_http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "sec-ch-ua": (
                f'"Google Chrome";v="{major_version}", '
                f'"Chromium";v="{major_version}", "Not-A.Brand";v="24"'
            ),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        },
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-notifications",
            "--disable-infobars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-features=IsolateOrigins,site-per-process,TranslateUI,MediaRouter",
            "--lang=pt-BR",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--macro-settings",
        action="store_true",
        help="Also test Patchright with local browser options from macro_arbitramento_imoveis",
    )
    parser.add_argument(
        "--reuse-macro-profile",
        action="store_true",
        help="Test Patchright with the persistent profile used by macro_arbitramento_imoveis",
    )
    parser.add_argument(
        "--native-chrome",
        action="store_true",
        help="Test visible Chrome with its native headers and a dedicated persistent profile",
    )
    parser.add_argument(
        "--save-html",
        type=Path,
        help="Save the rendered HTML after the expected feed items appear",
    )
    args = parser.parse_args()

    data = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    config = SiteConfig(**data)
    item_list = config.selectors.item_list
    selector = item_list.css or f"xpath={item_list.xpath}"

    if args.native_chrome:
        patchright_ok = check_browser(
            "Patchright (native Chrome, dedicated profile)",
            patchright_sync_playwright,
            PatchrightTimeoutError,
            config.source.url,
            selector,
            launch_options={
                "user_data_dir": str(Path.home() / ".risos" / "chrome-profile"),
                "channel": "chrome",
                "headless": False,
                "no_viewport": True,
            },
            persistent_context=True,
            wait_timeout=90_000,
            html_output=args.save_html,
        )
        print(f"Patchright with native Chrome: {'PASS' if patchright_ok else 'FAIL'}")
        return 0 if patchright_ok else 1

    if args.reuse_macro_profile:
        profile_dir = Path(tempfile.gettempdir()) / "arbitramento_pw_profile"
        if not profile_dir.is_dir():
            print(f"Macro browser profile not found: {profile_dir}")
            return 2
        patchright_ok = check_browser(
            "Patchright (macro settings, existing profile)",
            patchright_sync_playwright,
            PatchrightTimeoutError,
            config.source.url,
            selector,
            launch_options=macro_browser_options(str(profile_dir)),
            persistent_context=True,
        )
        print(f"Patchright with persistent macro profile: {'PASS' if patchright_ok else 'FAIL'}")
        return 0 if patchright_ok else 1

    playwright_ok = check_browser(
        "Playwright",
        playwright_sync_playwright,
        PlaywrightTimeoutError,
        config.source.url,
        selector,
    )
    patchright_ok = check_browser(
        "Patchright",
        patchright_sync_playwright,
        PatchrightTimeoutError,
        config.source.url,
        selector,
    )

    macro_patchright_ok = None
    if args.macro_settings:
        with tempfile.TemporaryDirectory(prefix="risos-macro-browser-") as profile_dir:
            macro_patchright_ok = check_browser(
                "Patchright (macro settings, fresh profile)",
                patchright_sync_playwright,
                PatchrightTimeoutError,
                config.source.url,
                selector,
                launch_options=macro_browser_options(profile_dir),
                persistent_context=True,
            )

    print("\n=== Comparison ===")
    print(f"Playwright: {'PASS' if playwright_ok else 'FAIL'}")
    print(f"Patchright: {'PASS' if patchright_ok else 'FAIL'}")
    if macro_patchright_ok is not None:
        print(f"Patchright (macro settings): {'PASS' if macro_patchright_ok else 'FAIL'}")
        return 0 if macro_patchright_ok else 1
    return 0 if patchright_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
