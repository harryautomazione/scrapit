#!/usr/bin/env bash
# create-issues.sh — create 50 scrapit GitHub issues (25 good-first-issue + 25 enhancement/bug/perf)
# Usage: bash create-issues.sh

set -euo pipefail

REPO="joaobenedetmachado/scrapit"

gh() { command gh "$@" --repo "$REPO"; }

echo "Creating 50 scrapit issues..."
echo

# ─────────────────────────────────────────────────────────────────────────────
# GOOD-FIRST-ISSUES (25)
# ────────

echo "[30/50] enhancement: dashboard authentication"
gh issue create \
  --title "feat: dashboard basic auth — protect scrapit serve behind a password" \
  --label "enhancement,security" \
  --body "## Problem
\`scrapit serve\` exposes scrape results and the ability to trigger new runs to anyone who can reach the port. On shared servers or when the dashboard is tunnelled publicly, this is a security risk.

## Proposal
Add optional HTTP Basic Auth controlled via env vars or CLI flag:

\`\`\`bash
scrapit serve --auth admin:secret
# or
SCRAPIT_DASHBOARD_USER=admin SCRAPIT_DASHBOARD_PASS=secret scrapit serve
\`\`\`

## Implementation
- FastAPI \`HTTPBasicCredentials\` dependency on all \`/api/*\` routes
- Skip auth when no credentials are configured
- Show 401 with \`WWW-Authenticate: Basic\` header

## Files
- \`scraper/dashboard.py\`"

echo "[31/50] enhancement: Prometheus metrics endpoint"
gh issue create \
  --title "feat: Prometheus metrics endpoint in scrapit serve (/metrics)" \
  --label "enhancement" \
  --body "## Problem
There is no observability layer for production scrapit deployments. Teams cannot alert on scrape failure rates, latency, or field coverage.

## Proposal
Expose a \`/metrics\` endpoint (Prometheus text format) on the dashboard server:

\`\`\`
# HELP scrapit_scrape_total Total scrapes by directive
# TYPE scrapit_scrape_total counter
scrapit_scrape_total{directive=\"hn\",status=\"ok\"} 42
scrapit_scrape_duration_seconds{directive=\"hn\",quantile=\"0.99\"} 3.14
scrapit_fields_coverage{directive=\"hn\"} 0.97
\`\`\`

## Implementation
- \`prometheus_client\` optional dependency
- Counters/histograms updated in \`ScrapeStats.stop()\`
- Route \`GET /metrics\` returns text exposition

## Files
- \`scraper/reporter.py\`
- \`scraper/dashboard.py\`"

echo "[32/50] enhancement: RSS/XML feed scraper backend"
gh issue create \
  --title "feat: RSS/XML feed scraper backend (use: rss)" \
  --label "enhancement" \
  --body "## Problem
News aggregation is a common scraping use case but RSS/Atom feeds require XML parsing, not CSS selectors. Users must resort to the bs4 backend and write fragile selectors.

## Proposal
Add \`use: rss\` backend that parses RSS/Atom feeds natively:

\`\`\`yaml
site: https://hnrss.org/frontpage
use: rss

scrape:
  title:       { path: title }
  link:        { path: link }
  published:   { path: published }
  description: { path: summary }
\`\`\`

## Implementation
- \`scraper/scrapers/rss_scraper.py\` using \`feedparser\`
- Optional dep: \`scrapit[rss]\`
- Returns list of entries as dicts

## Files
- \`scraper/scrapers/rss_scraper.py\` (new)
- \`scraper/scrapers/__init__.py\`"

echo "[33/50] enhancement: Celery task queue integration"
gh issue create \
  --title "feat: Celery integration — dispatch directive scrapes as distributed tasks" \
  --label "enhancement" \
  --body "## Problem
The RabbitMQ producer/consumer (\`scraper/queue/\`) is incomplete and tightly coupled to RabbitMQ. Modern teams use Celery for distributed task execution with support for Redis, SQS, and other brokers.

## Proposal
Add a \`celery\` backend for the queue:

\`\`\`bash
scrapit scrape hn --queue celery
\`\`\`

Dispatches the scrape as a Celery task instead of running synchronously.

## Implementation
- \`scraper/queue/celery_backend.py\`
- Task: \`@app.task def run_directive(path, dest, **kw)\`
- Optional dep: \`scrapit[celery]\`

## Files
- \`scraper/queue/celery_backend.py\` (new)
- \`scraper/main.py\` — \`--queue\` flag"

echo "[34/50] enhancement: multi-instance state locking with Redis"
gh issue create \
  --title "feat: distributed state locking — prevent concurrent runs of same directive" \
  --label "enhancement,reliability" \
  --body "## Problem
Running the same directive concurrently (e.g. via cron overlap or multiple \`scrapit run\` daemons) can corrupt spider checkpoints and cause duplicate writes to SQLite/CSV.

## Proposal
Use Redis \`SET NX EX\` locks to ensure only one instance of a given directive runs at a time:

\`\`\`
lock key: scrapit:lock:<directive_name>
TTL: max_expected_runtime (default: 3600s)
\`\`\`

If the lock is held, log a warning and skip the run.

## Files
- \`scraper/lock.py\` (new)
- \`scraper/scrapers/__init__.py\`
- \`scraper/main.py\`"

echo "[35/50] enhancement: data versioning with snapshots"
gh issue create \
  --title "feat: data versioning — keep N previous output snapshots per directive" \
  --label "enhancement" \
  --body "## Problem
\`output/directive.json\` is overwritten on every run. If a scrape produces bad data (selector broke, site changed), the previous good data is lost.

## Proposal
Add a \`versions:\` config that keeps the last N snapshots:

\`\`\`yaml
output:
  versions: 5   # keep last 5 runs
\`\`\`

Files would be stored as \`output/directive.2026-03-09T12:00:00.json\` with a symlink at \`output/directive.json\` pointing to the latest.

## Files
- \`scraper/storage/json_file.py\`
- \`scraper/main.py\`"

echo "[36/50] bug: SQLite dedup uses fragile LIKE string matching"
gh issue create \
  --title "fix: SQLite unique_on uses LIKE matching — replace with exact JSON field extraction" \
  --label "bug,reliability" \
  --body "## Problem
The \`unique_on\` deduplication in \`scraper/storage/sqlite.py\` uses:
\`\`\`python
conn.execute(\"SELECT id FROM scrapes WHERE directive = ? AND data LIKE ?\",
             (directive_name, f\"%{composite_key}%\"))
\`\`\`

This is fragile: a value that is a substring of another field's value will produce false positive duplicates.

## Proposal
Use SQLite's \`json_extract\` function to compare field values exactly:
\`\`\`sql
WHERE directive = ? AND json_extract(data, '$.url') = ?
\`\`\`

## Files
- \`scraper/storage/sqlite.py\` — \`save\` function"

echo "[37/50] enhancement: watch mode for directive development"
gh issue create \
  --title "feat: scrapit watch — auto-rerun directive on file change" \
  --label "enhancement" \
  --body "## Problem
During directive development, users must manually re-run \`scrapit scrape directive --preview\` after every YAML edit. This breaks the feedback loop.

## Proposal
Add a \`watch\` subcommand using \`watchfiles\` (or \`watchdog\`) that reruns the directive on save:

\`\`\`bash
scrapit watch hn --preview
# → watching scraper/directives/hn.yaml
# → [change detected] re-running...
\`\`\`

## Implementation
- Optional dep: \`watchfiles\` (already pulled in by many frameworks)
- Loop: watch YAML file, on change run \`_run_one\` with \`preview=True\`

## Files
- \`scraper/main.py\` — \`cmd_watch\` (new)
- \`pyproject.toml\` — \`watch\` extra"

echo "[38/50] enhancement: directive JSON Schema generation"
gh issue create \
  --title "feat: scrapit schema — generate JSON Schema for directive YAML validation" \
  --label "enhancement,developer-experience" \
  --body "## Problem
There is no machine-readable schema for directive YAML files. Editors cannot validate or autocomplete fields like \`use:\`, \`transform:\`, \`validate:\`, \`follow:\` etc.

## Proposal
Add \`scrapit schema\` command that prints a JSON Schema to stdout:

\`\`\`bash
scrapit schema > .scrapit.schema.json
# Point your editor/IDE schema store to this file
\`\`\`

## Implementation
- Hardcode or generate the schema from introspection
- Include \`$defs\` for transform names (from \`_REGISTRY\`)
- Publish schema to SchemaStore PR

## Files
- \`scraper/main.py\` — \`cmd_schema\`
- \`scraper/schema.py\` (new)"

echo "[39/50] performance: connection pooling for bs4 backend"
gh issue create \
  --title "perf: use requests.Session for connection pooling in bs4_scraper" \
  --label "performance" \
  --body "## Problem
\`bs4_scraper.fetch_html\` creates a new \`requests.get\` call each time. \`requests\` creates a new TCP connection per call, which is wasteful for paginated/spider runs against the same host.

## Proposal
Use a \`requests.Session\` that is shared across fetches within a single directive run. This enables HTTP keep-alive and reduces TLS handshake overhead.

## Implementation
- Pass an optional \`session: requests.Session\` into \`fetch_html\`
- Create the session once in \`scrape()\` and reuse it across the retry loop
- \`Spider._fetch_kw\` passes the session down

## Files
- \`scraper/scrapers/bs4_scraper.py\`
- \`scraper/scrapers/spider.py\`"

echo "[40/50] performance: bounded file cache with LRU eviction"
gh issue create \
  --title "perf: add max_size to file cache to prevent unbounded .cache/ growth" \
  --label "performance,reliability" \
  --body "## Problem
The file-based HTTP cache at \`.cache/\` grows indefinitely. There is no maximum size limit. Long-running scrapit deployments accumulate gigabytes of cached HTML.

## Proposal
Add a \`cache.max_size_mb:\` directive option. When exceeded, evict the least-recently-used entries:

\`\`\`yaml
cache:
  ttl: 3600
  max_size_mb: 500
\`\`\`

## Implementation
- After each \`put\`, check total \`.cache/\` size
- If over limit, delete oldest \`.meta\` files first

## Files
- \`scraper/cache/__init__.py\`"

echo "[41/50] reliability: webhook notification retry logic"
gh issue create \
  --title "fix: webhook notifications have no retry on transient network errors" \
  --label "bug,reliability" \
  --body "## Problem
\`scraper/notifications/__init__.py\` sends webhook (Slack/Discord) notifications with a single \`requests.post\` call. A transient network error silently drops the alert.

## Proposal
Add exponential backoff retry (up to 3 attempts) for webhook delivery, consistent with \`bs4_scraper.fetch_html\`.

\`\`\`python
for attempt in range(3):
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        break
    except requests.RequestException:
        time.sleep(2 ** attempt)
\`\`\`

## Files
- \`scraper/notifications/__init__.py\`"

echo "[42/50] enhancement: Playwright iframe support"
gh issue create \
  --title "feat: Playwright backend — support scraping inside iframes" \
  --label "enhancement" \
  --body "## Problem
Many sites embed content in \`<iframe>\` elements (ads, embedded widgets, login forms). The Playwright backend has no way to switch frame context during scraping.

## Proposal
Add a \`frame:\` key to the directive that locates an iframe by selector or name before applying scrape specs:

\`\`\`yaml
use: playwright
frame: 'iframe#content'

scrape:
  price: ['.price']
\`\`\`

## Implementation
- In \`playwright_scraper.scrape\`, after \`page.goto\`, call \`page.frame_locator(frame_sel).locator(...)\` when \`frame:\` is set

## Files
- \`scraper/scrapers/playwright_scraper.py\`"

echo "[43/50] enhancement: Playwright intercept/mock network requests"
gh issue create \
  --title "feat: Playwright backend — block or mock network requests via directive" \
  --label "enhancement" \
  --body "## Problem
JS-heavy pages load dozens of tracking scripts, ads, and analytics. These slow scrapes and waste bandwidth. Playwright can intercept and abort them but scrapit exposes no directive for this.

## Proposal
Add a \`block_resources:\` directive key:

\`\`\`yaml
use: playwright
block_resources:
  - image
  - media
  - font
  - analytics.google.com
\`\`\`

## Implementation
- \`page.route\` handler that aborts requests matching type or URL pattern

## Files
- \`scraper/scrapers/playwright_scraper.py\`"

echo "[44/50] enhancement: scrape multiple elements with sub-specs"
gh issue create \
  --title "feat: nested scrape spec — extract list of objects from repeated elements" \
  --label "enhancement" \
  --body "## Problem
\`all: true\` returns a flat list of strings. There is no way to extract multiple fields from each repeated element (e.g. list of {title, link, score} from each HN item).

## Proposal
Support a \`fields:\` sub-spec inside scrape definitions:

\`\`\`yaml
scrape:
  items:
    - '.athing'
    - all: true
      fields:
        title: ['.titleline > a']
        score: ['.score']
        link:  ['.titleline > a', {attr: href}]
\`\`\`

Returns: \`[{title: ..., score: ..., link: ...}, ...]\`

## Files
- \`scraper/scrapers/bs4_scraper.py\` — \`parse_page\`"

echo "[45/50] enhancement: AI-powered field extraction (LLM fallback)"
gh issue create \
  --title "feat: llm_extract transform — use Claude to extract a field when CSS selector fails" \
  --label "enhancement" \
  --body "## Problem
CSS selectors break when sites change their HTML. Users must manually update directives after every site redesign. An LLM fallback could maintain coverage automatically.

## Proposal
Add an \`llm_extract:\` transform that sends the raw HTML snippet to Claude when a field is \`null\`:

\`\`\`yaml
scrape:
  price:
    - '.price-box'
    - attr: text
      on_missing: null

transform:
  price:
    - default: null
    - llm_extract: 'Extract the product price as a number. Return only the number.'
\`\`\`

## Files
- \`scraper/transforms/__init__.py\`
- \`scraper/integrations/anthropic.py\`"

echo "[46/50] enhancement: output field filtering"
gh issue create \
  --title "feat: output.include / output.exclude — filter fields from saved result" \
  --label "enhancement" \
  --body "## Problem
Directives often scrape more fields than the consumer needs (e.g. debug fields, internal metadata). All fields are always saved, increasing storage footprint.

## Proposal
Add \`output:\` block to directive for field selection:

\`\`\`yaml
output:
  exclude: [url, timestamp, _valid, _errors]
  # or:
  include: [title, price, link]
\`\`\`

## Implementation
After transforms/validation, filter the result dict before passing to storage.

## Files
- \`scraper/scrapers/__init__.py\`"

echo "[47/50] enhancement: dashboard time-series graph"
gh issue create \
  --title "feat: dashboard — time-series graph showing scrape coverage and field counts over time" \
  --label "enhancement" \
  --body "## Problem
The dashboard shows the latest scrape result but no historical trends. Teams cannot spot regressions (e.g. price field dropping to null) without manually comparing JSON files.

## Proposal
Add a time-series chart (using Chart.js CDN, no extra server deps) to the directive detail view:
- X axis: run timestamp
- Y axis: field coverage % and record count

Requires SQLite backend to store run history.

## Files
- \`scraper/dashboard.py\`
- \`scraper/storage/sqlite.py\` — add run_history table"

echo "[48/50] enhancement: field-level extraction confidence score"
gh issue create \
  --title "feat: report extraction confidence per field (found %, selector match rate)" \
  --label "enhancement" \
  --body "## Problem
\`ScrapeStats\` tracks total fields found/missing but not per-field. In spider mode with 100 pages, a field that is missing on 30% of pages silently degrades data quality.

## Proposal
Track per-field extraction counts across multi-page runs and include in the stats summary:

\`\`\`
field coverage:
  title   100/100 (100%)
  price    87/100 (87%)  ← warning
  rating   12/100 (12%)  ← critical
\`\`\`

Print the low-coverage fields as warnings.

## Files
- \`scraper/reporter.py\`
- \`scraper/scrapers/__init__.py\`"

echo "[49/50] enhancement: scrapit export --format parquet auto-schema"
gh issue create \
  --title "feat: scrapit export infers Parquet schema from SQLite data types" \
  --label "enhancement" \
  --body "## Problem
\`scraper/storage/parquet_file.py\` uses \`pyarrow.Table.from_pylist\` which infers all types as strings (since SQLite stores data as JSON strings). Numeric and date fields lose their native types in Parquet.

## Proposal
After reading records from SQLite, attempt type inference:
- Fields where all values are valid \`int\` → \`pa.int64()\`
- Fields where all values are valid \`float\` → \`pa.float64()\`
- Fields where all values match ISO date → \`pa.date32()\`

## Files
- \`scraper/storage/parquet_file.py\`
- \`scraper/storage/sqlite.py\` — \`read()\`"

echo "[50/50] enhancement: YAML anchors for shared directive sections"
gh issue create \
  --title "feat: document and test YAML anchor support in directives (&anchor / *alias)" \
  --label "enhancement,documentation" \
  --body "## Problem
YAML anchors (\`&anchor\` / \`*alias\`) allow DRY config reuse within a single file. It is unclear whether scrapit supports them since \`yaml.safe_load\` handles them natively, but this is undocumented and untested.

## Proposal
1. Add a test verifying anchor/alias is resolved correctly after \`yaml.safe_load\`
2. Add an example in docs/directives.md showing shared headers across multiple scrape specs
3. Document the limitation: anchors only work within one file (cross-file requires \`extends:\`)

\`\`\`yaml
_auth: &auth
  headers:
    Authorization: 'Bearer \${TOKEN}'

site: https://api.example.com/users
use: rest
<<: *auth
scrape:
  name: { path: name }
\`\`\`

## Files
- \`tests/test_directives.py\` (new or existing)
- \`docs/\`"

echo
echo "✓ All 50 issues created."
