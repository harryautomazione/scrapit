# Contributing to Scrapit

First off — thanks for taking the time to contribute! Every contribution helps, whether it's a new directive, a bug fix, a new transform, or just improving the docs.

---

## Ways to Contribute

| Type | Examples |
|------|---------|
| **Share a directive** | Add a YAML for a site you scraped and it worked |
| **Bug fix** | Fix broken behavior or edge cases |
| **New transform** | Add a new transform to `scraper/transforms/__init__.py` |
| **New storage backend** | Add an exporter (e.g. PostgreSQL, Google Sheets) |
| **New scraper backend** | Add support for another fetching library |
| **Docs** | Improve examples, fix typos, translate |
| **Tests** | Add test coverage for any module |

---

## Getting Started

### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/scrapit.git
cd scrapit
```

### 2. Set up your environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # linting and test tools
```

### 3. Create a branch

Use a descriptive branch name:

```bash
git checkout -b feat/new-transform-slugify
git checkout -b fix/playwright-timeout
git checkout -b directive/hacker-news
```

### 4. Make your changes

Follow the patterns already in the codebase. See the sections below for specifics.

### 5. Open a Pull Request

Push your branch and open a PR against `main`. Fill in the PR template.

---

## Adding a New Transform

Transforms live in `scraper/transforms/__init__.py`. Adding one is straightforward:

```python
@_t("slugify")
def _slugify(value, _, **__):
    if not isinstance(value, str):
        return value
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
```

Then document it in the table in `README.md` and `CONTRIBUTING.md`.

---

## Adding a New Storage Backend

Create `scraper/storage/<name>.py` with at minimum:

```python
def save(data: dict, directive_name: str) -> str:
    """Save scraped data. Return a string describing where it was saved."""
    ...
```

Then wire it into `scraper/main.py` under `_save()` and `_add_output_args()`.

---

## Sharing a Directive

The best contributions are real-world directives that work! Place your YAML in `scraper/directives/` and make sure it:

1. Has a comment at the top explaining the site and what it scrapes
2. Has a `# Usage:` comment showing the CLI command
3. Uses `cache: {ttl: N}` to avoid hammering the site during dev
4. Includes `transform:` and `validate:` where appropriate

See `scraper/directives/books.yaml` for a good example.

---

## Code Style

- Python 3.10+
- Keep functions small and focused
- No unused imports
- Type hints on public function signatures
- Docstrings on public modules and non-obvious functions

We don't enforce a strict formatter right now, but try to match the style of existing code.

---

## Commit Messages

Use conventional commits format:

```
feat: add slugify transform
fix: handle None in regex transform
directive: add books.toscrape.com example
docs: add proxy configuration example
refactor: extract _parse_page from bs4_scraper
test: add validator edge cases
```

---

## Questions?

Open a [GitHub Discussion](https://github.com/joaobenedetmachado/scrapit/discussions) or file an issue. We're happy to help you get started.
