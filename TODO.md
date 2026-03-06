# Scrapit — TODO

All major items completed. Below are remaining stretch goals.

## ✅ Done

- Bugs fixed: openpyxl dep, lazy excel import, MCP all_matches, link_limit
- MCP: scrape_many, scrape_paginated, run_batch, generate_directive tools
- Core: XPath selectors, user-agent rotation, robots.txt, rate limiting, data dedup
- CLI: scrapit init, ai-init, suggest-selectors, share, doctor, --format, --resume
- Spider: checkpoint/resume interrupted scrapes
- DX: VS Code JSON schema, GitHub Action template, badge
- Tests: transforms, validators, storage, MCP integration tests
- CI: pytest-cov, tests now fail CI properly

---

## 🔵 Stretch Goals

- [ ] **`scrapit ai-init` with OpenAI** — currently Claude-only, add `--model gpt-4o` flag
- [ ] **Async concurrent scraping with httpx** — replace ThreadPoolExecutor in scrape_many with native async
- [ ] **Directive registry website** — public site where users browse/submit community directives
- [ ] **`scrapit share` registry** — POST to a registry API instead of GitHub issues
- [ ] **Test Playwright backend** — zero tests for playwright_scraper.py
- [ ] **Better YAML validation errors** — show line number + field name when directive is malformed
- [ ] **`scrapit suggest-selectors` with OpenAI** — add `--model` flag
- [ ] **Smart pagination detection** — auto-detect next-page patterns without manual config
- [ ] **Paginator checkpoint/resume** — save page number on interruption (spider resume done)
- [ ] **Type hints throughout** — bs4_scraper.py, transforms, validators still have gaps
