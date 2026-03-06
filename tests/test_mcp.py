"""
Integration tests for the MCP server tools.

Tests call the underlying integration functions directly (no MCP transport needed).
HTTP calls are mocked so tests run offline and fast.
"""

from unittest.mock import patch, MagicMock
import json
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_HTML = """
<html>
<head>
  <title>Test Page</title>
  <meta name="description" content="A test page for scrapit">
</head>
<body>
  <h1>Hello World</h1>
  <p class="price">£12.99</p>
  <a href="https://example.com/page2">Next</a>
  <a href="https://external.com">External</a>
</body>
</html>
"""

_MOCK_RESPONSE = MagicMock()
_MOCK_RESPONSE.text = FAKE_HTML
_MOCK_RESPONSE.raise_for_status = MagicMock()


def _mock_get(*args, **kwargs):
    return _MOCK_RESPONSE


# ── scrape_url ─────────────────────────────────────────────────────────────────

class TestScrapeUrl:
    @patch("requests.get", side_effect=_mock_get)
    def test_returns_plain_text(self, _):
        from scraper.integrations import scrape_url
        result = scrape_url("https://example.com")
        assert isinstance(result, str)
        assert "Hello World" in result

    @patch("requests.get", side_effect=_mock_get)
    def test_strips_scripts_and_nav(self, _):
        from scraper.integrations import scrape_url
        result = scrape_url("https://example.com")
        assert "<script>" not in result
        assert "<nav>" not in result


# ── scrape_page ───────────────────────────────────────────────────────────────

class TestScrapePage:
    @patch("requests.get", side_effect=_mock_get)
    def test_returns_structured_dict(self, _):
        from scraper.integrations import scrape_page
        page = scrape_page("https://example.com")
        assert page["title"] == "Test Page"
        assert page["description"] == "A test page for scrapit"
        assert isinstance(page["links"], list)
        assert isinstance(page["word_count"], int)
        assert page["word_count"] > 0

    @patch("requests.get", side_effect=_mock_get)
    def test_links_are_absolute_http(self, _):
        from scraper.integrations import scrape_page
        page = scrape_page("https://example.com")
        for link in page["links"]:
            assert link.startswith("http")

    @patch("requests.get", side_effect=_mock_get)
    def test_url_field_present(self, _):
        from scraper.integrations import scrape_page
        page = scrape_page("https://example.com")
        assert page["url"] == "https://example.com"


# ── scrape_with_selectors ──────────────────────────────────────────────────────

class TestScrapeWithSelectors:
    @patch("requests.get", side_effect=_mock_get)
    def test_extracts_single_field(self, _):
        from scraper.integrations import scrape_with_selectors
        result = scrape_with_selectors("https://example.com", {"heading": "h1"})
        assert result["heading"] == "Hello World"

    @patch("requests.get", side_effect=_mock_get)
    def test_missing_selector_returns_none(self, _):
        from scraper.integrations import scrape_with_selectors
        result = scrape_with_selectors("https://example.com", {"missing": ".nonexistent"})
        assert result["missing"] is None

    @patch("requests.get", side_effect=_mock_get)
    def test_all_matches(self, _):
        from scraper.integrations import scrape_with_selectors
        result = scrape_with_selectors(
            "https://example.com",
            {"links": "a"},
            all_matches={"links": True},
        )
        assert isinstance(result["links"], list)
        assert len(result["links"]) >= 1

    @patch("requests.get", side_effect=_mock_get)
    def test_ok_and_url_fields(self, _):
        from scraper.integrations import scrape_with_selectors
        result = scrape_with_selectors("https://example.com", {"h": "h1"})
        assert result["ok"] is True
        assert result["url"] == "https://example.com"


# ── scrape_many ───────────────────────────────────────────────────────────────

class TestScrapeMany:
    @patch("requests.get", side_effect=_mock_get)
    def test_returns_list_same_length(self, _):
        from scraper.integrations import scrape_many
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        results = scrape_many(urls, mode="text")
        assert len(results) == 3

    @patch("requests.get", side_effect=_mock_get)
    def test_text_mode(self, _):
        from scraper.integrations import scrape_many
        results = scrape_many(["https://example.com"], mode="text")
        assert "text" in results[0]
        assert isinstance(results[0]["text"], str)

    @patch("requests.get", side_effect=_mock_get)
    def test_page_mode(self, _):
        from scraper.integrations import scrape_many
        results = scrape_many(["https://example.com"], mode="page")
        assert "title" in results[0]
        assert "links" in results[0]

    @patch("requests.get", side_effect=_mock_get)
    def test_preserves_order(self, _):
        from scraper.integrations import scrape_many
        urls = ["https://first.com", "https://second.com"]
        results = scrape_many(urls)
        assert results[0]["url"] == "https://first.com"
        assert results[1]["url"] == "https://second.com"


# ── MCP server creation ────────────────────────────────────────────────────────

class TestMCPServer:
    def test_create_server_requires_mcp(self):
        """create_server() raises ImportError if mcp package is missing."""
        import sys
        mcp_backup = sys.modules.get("mcp")
        sys.modules["mcp"] = None  # type: ignore
        sys.modules.pop("mcp.server", None)
        sys.modules.pop("mcp.server.fastmcp", None)
        try:
            from scraper.integrations import mcp as mcp_module
            import importlib
            importlib.reload(mcp_module)
            with pytest.raises((ImportError, TypeError)):
                mcp_module.create_server()
        finally:
            if mcp_backup is not None:
                sys.modules["mcp"] = mcp_backup
            else:
                sys.modules.pop("mcp", None)
