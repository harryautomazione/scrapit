"""
Bright Data integration — proxy network and Scraping Browser.

Two modes:

1. Proxy mode (`use: bs4` or `use: playwright` + `proxy: brightdata`)
   Routes requests through Bright Data residential proxies.
   Requires: BRIGHTDATA_HOST, BRIGHTDATA_PORT, BRIGHTDATA_USERNAME, BRIGHTDATA_PASSWORD

2. Scraping Browser mode (`use: brightdata`)
   Uses Bright Data's managed Scraping Browser (CDP/WebSocket).
   Handles CAPTCHAs, TLS fingerprinting, and bot detection automatically.
   Requires: BRIGHTDATA_WS_ENDPOINT  (wss://brd-customer-XXX-zone-YYY:PASSWORD@brd.superproxy.io:9222)

Environment variables (.env):
  BRIGHTDATA_USERNAME      — Bright Data zone username
  BRIGHTDATA_PASSWORD      — Bright Data zone password
  BRIGHTDATA_HOST          — proxy host (default: brd.superproxy.io)
  BRIGHTDATA_PORT          — proxy port (default: 22225)
  BRIGHTDATA_WS_ENDPOINT   — WebSocket endpoint for Scraping Browser mode
"""

import os
from datetime import datetime

from scraper.config import OUTPUT_DIR


def proxy_url() -> str:
    """Build the Bright Data proxy URL from environment variables."""
    host = os.environ.get("BRIGHTDATA_HOST", "brd.superproxy.io")
    port = os.environ.get("BRIGHTDATA_PORT", "22225")
    user = os.environ.get("BRIGHTDATA_USERNAME", "")
    password = os.environ.get("BRIGHTDATA_PASSWORD", "")

    if not user or not password:
        raise EnvironmentError(
            "Bright Data proxy requires BRIGHTDATA_USERNAME and BRIGHTDATA_PASSWORD env vars.\n"
            "Add them to your .env file."
        )
    return f"http://{user}:{password}@{host}:{port}"


def ws_endpoint() -> str:
    """Return the Bright Data Scraping Browser WebSocket endpoint."""
    endpoint = os.environ.get("BRIGHTDATA_WS_ENDPOINT", "")
    if not endpoint:
        raise EnvironmentError(
            "Bright Data Scraping Browser requires BRIGHTDATA_WS_ENDPOINT env var.\n"
            "Format: wss://brd-customer-XXX-zone-YYY:PASSWORD@brd.superproxy.io:9222\n"
            "Add it to your .env file."
        )
    return endpoint


async def scrape(dados: dict, directive_name: str = "") -> dict:
    """
    Scrape using Bright Data's Scraping Browser (use: brightdata).

    Connects to the managed browser via WebSocket CDP endpoint.
    Handles bot detection, CAPTCHAs, and JS rendering automatically.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError("playwright required: pip install playwright && playwright install chromium")

    import asyncio
    endpoint = ws_endpoint()
    timeout_ms = dados.get("timeout", 60_000)
    wait_for = dados.get("wait_for")
    delay = dados.get("delay", 0)

    if delay > 0:
        await asyncio.sleep(delay)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(endpoint)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        if headers := dados.get("headers"):
            await page.set_extra_http_headers(headers)

        await page.goto(dados["site"], timeout=timeout_ms, wait_until="domcontentloaded")

        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout_ms)
        else:
            await page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 30_000))

        result = {}
        for key, value in dados["scrape"].items():
            selectors_raw = value[0]
            options = value[1] if len(value) > 1 else {}
            attr = options.get("attr", "text")
            get_all = options.get("all", False)

            selectors = selectors_raw if isinstance(selectors_raw, list) else [selectors_raw]

            locator = None
            for sel in selectors:
                try:
                    await page.wait_for_selector(sel, timeout=5_000)
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        locator = loc
                        break
                except Exception:
                    pass

            if locator is None or await locator.count() == 0:
                result[key] = [] if get_all else None
                continue

            if get_all:
                count = await locator.count()
                items = []
                for i in range(count):
                    items.append(await _get_attr(locator.nth(i), attr))
                result[key] = items
            else:
                result[key] = await _get_attr(locator.first, attr)

        if dados.get("screenshot"):
            OUTPUT_DIR.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shot_path = OUTPUT_DIR / f"{directive_name or 'brightdata'}_{ts}.png"
            await page.screenshot(path=str(shot_path), full_page=True)
            result["_screenshot"] = str(shot_path)

        await browser.close()

    result["url"] = dados["site"]
    result["timestamp"] = datetime.now()
    return result


async def _get_attr(locator, attr: str):
    if attr == "text":
        return await locator.inner_text()
    elif attr == "html":
        return await locator.inner_html()
    else:
        return await locator.get_attribute(attr)
