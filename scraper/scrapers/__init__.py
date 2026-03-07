"""
Scraper dispatcher — orchestrates the full scrape pipeline:

  load YAML → dispatch to backend → transforms → validate → hooks → return

Directive `mode` values:
  (default)  — single URL, no pagination
  spider     — follow links from index page

Extra directive keys handled here:
  mode: spider
  follow: {...}       — spider config
  sites: [url, ...]   — scrape multiple URLs with same spec
  paginate: {...}     — follow "next page" links (bs4 only)
  transform: {...}    — per-field transforms applied after scraping
  validate: {...}     — per-field validation rules
"""

import os
import re
import time
import yaml
from pathlib import Path

from scraper import transforms as _transforms
from scraper import validators as _validators
from scraper import hooks
from scraper.reporter import ScrapeStats, count_fields
from scraper.logger import log


# Required keys for directive validation
_REQUIRED_KEYS = ["site", "use", "scrape"]


def _validate_directive(dados: dict, path: str):
    """
    Validate that directive YAML has all required keys.
    
    Args:
        dados: Loaded YAML dictionary
        path: Directive file path (for error messages)
    
    Raises:
        ValueError: If required keys are missing
    """
    # Check for 'sites' key (alternative to 'site')
    has_site = "site" in dados
    has_sites = "sites" in dados
    
    missing = []
    for key in _REQUIRED_KEYS:
        if key == "site":
            # Either 'site' or 'sites' is acceptable
            if not has_site and not has_sites:
                missing.append(key)
        else:
            if key not in dados:
                missing.append(key)
    
    if missing:
        directive_name = Path(path).stem
        missing_str = ", ".join(missing)
        all_keys = ", ".join(_REQUIRED_KEYS)
        raise ValueError(
            f"Directive '{directive_name}' is missing required key(s): {missing_str}\n"
            f"Required keys: {all_keys}"
        )


def _interpolate_env(obj):
    """Recursively replace ${VAR} placeholders in directive strings with env vars."""
    if isinstance(obj, str):
        return re.sub(r"\$\{([^}]+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), obj)
    if isinstance(obj, dict):
        return {k: _interpolate_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_interpolate_env(v) for v in obj]
    return obj


async def grab_elements_by_directive(path: str, resume: bool = False, timeout: int | None = None) -> dict | list[dict]:
    """
    Main entry point. Returns a single dict for simple scrapes,
    or a list of dicts for paginated / spider / multi-site scrapes.

    timeout: per-request timeout in seconds (overrides directive-level setting).
    """
    with open(path) as f:
        dados = yaml.safe_load(f)

    dados = _interpolate_env(dados)

    if timeout is not None:
        dados["timeout"] = timeout

    # Validate directive has required keys
    _validate_directive(dados, path)

    directive_name = Path(path).stem
    stats = ScrapeStats(directive=directive_name, url=dados.get("site", ""))
    hooks.fire("before_scrape", dados)

    try:
        results = await _dispatch(dados, stats, directive_name, resume=resume)
    except Exception as e:
        stats.errors.append(str(e))
        hooks.fire("on_error", e, dados)
        raise

    # Apply per-field transforms
    if transform_spec := dados.get("transform"):
        results = [_transforms.apply_all(r, transform_spec) for r in results]

    # Validate each result
    if validate_spec := dados.get("validate"):
        for r in results:
            report = _validators.validate(r, validate_spec)
            if not report.valid:
                log(f"validation issues for {directive_name}:\n{report}", "warning")
            r["_valid"] = report.valid
            r["_errors"] = [str(e) for e in report.errors]

    # Stats
    stats.stop()
    stats.urls_scraped = len(results)
    if results:
        found, missing = count_fields(results[0])
        stats.fields_found = found
        stats.fields_missing = missing

    log(stats.summary())

    for r in results:
        hooks.fire("after_scrape", r, dados)

    return results[0] if len(results) == 1 else results


async def _dispatch(dados: dict, stats: ScrapeStats, directive_name: str, resume: bool = False) -> list[dict]:
    from scraper.scrapers import bs4_scraper, playwright_scraper
    from scraper.scrapers.paginator import paginate
    from scraper.scrapers.spider import Spider

    use = dados.get("use", "beautifulsoup")
    mode = dados.get("mode", "single")
    has_follow = bool(dados.get("follow"))
    has_sites = bool(dados.get("sites"))
    has_paginate = bool(dados.get("paginate"))

    # ── Multi-site ────────────────────────────────────────────────────────────
    if has_sites:
        results = []
        delay = dados.get("delay", 0)
        for idx, url in enumerate(dados["sites"]):
            site_dados = {**dados, "site": url}
            site_dados.pop("sites", None)
            if use == "beautifulsoup":
                results.append(bs4_scraper.scrape(site_dados))
            else:
                results.append(await playwright_scraper.scrape(site_dados, directive_name))
            # Apply delay between multi-site requests (skip after last)
            if delay > 0 and idx < len(dados["sites"]) - 1:
                time.sleep(delay)
        stats.urls_scraped = len(results)
        return results

    # ── Spider mode ───────────────────────────────────────────────────────────
    if mode == "spider" or has_follow:
        if use != "beautifulsoup":
            raise ValueError("Spider mode only supports 'beautifulsoup' backend.")
        spider = Spider(dados, resume=resume)
        results = spider.run(directive_name=directive_name)
        stats.urls_scraped = len(results)
        return results

    # ── Paginated (bs4 only) ──────────────────────────────────────────────────
    if has_paginate:
        if use != "beautifulsoup":
            raise ValueError("Pagination only supports 'beautifulsoup' backend.")
        results = paginate(dados)
        stats.pages_scraped = len(results)
        stats.urls_scraped = len(results)
        return results

    # ── Single URL ────────────────────────────────────────────────────────────
    if use == "beautifulsoup":
        return [bs4_scraper.scrape(dados)]
    elif use == "playwright":
        return [await playwright_scraper.scrape(dados, directive_name)]
    else:
        raise ValueError(f"Unknown backend: {use!r}. Use 'beautifulsoup' or 'playwright'.")
