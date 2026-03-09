"""
httpx scraper backend — async-capable alternative to the requests/bs4 backend.

Directive options:
  use: httpx
  site: url
  scrape: ...            — same format as bs4_scraper
  headers: {}
  cookies: {}
  proxy: "http://..."
  retries: 3
  timeout: 15
  delay: 1.0
"""

import time
import random
import httpx
from bs4 import BeautifulSoup
from datetime import datetime

from scraper.scrapers.bs4_scraper import parse_page, _USER_AGENTS


def scrape(dados: dict) -> dict:
    delay = dados.get("delay", 0)
    if delay > 0:
        time.sleep(delay)

    url     = dados["site"]
    timeout = dados.get("timeout", 15)
    retries = dados.get("retries", 3)
    headers = {"User-Agent": random.choice(_USER_AGENTS), **(dados.get("headers") or {})}
    cookies = dados.get("cookies") or {}
    proxy   = dados.get("proxy")

    transport = httpx.HTTPTransport(proxy=proxy) if proxy else None
    last_exc  = None

    for attempt in range(retries):
        try:
            with httpx.Client(transport=transport, timeout=timeout) as client:
                resp = client.get(url, headers=headers, cookies=cookies)
                resp.raise_for_status()
                html = resp.text
                break
        except httpx.HTTPError as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    else:
        raise last_exc

    soup = BeautifulSoup(html, "html.parser")
    result = parse_page(soup, url, dados["scrape"], raw_html=html)
    result["url"] = url
    result["timestamp"] = datetime.now()
    return result
