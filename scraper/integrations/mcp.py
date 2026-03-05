"""
MCP (Model Context Protocol) server for Scrapit.

Exposes Scrapit as an MCP server, making it available as a native tool in:
- Claude Desktop
- Claude Code (claude.ai/code)
- Cursor
- Any MCP-compatible AI client

Installation:

    pip install mcp

Running the server:

    python -m scraper.integrations.mcp

Adding to Claude Desktop (~/Library/Application Support/Claude/claude_desktop_config.json):

    {
      "mcpServers": {
        "scrapit": {
          "command": "python",
          "args": ["-m", "scraper.integrations.mcp"],
          "cwd": "/path/to/your/scrapit"
        }
      }
    }

Adding to Claude Code:

    claude mcp add scrapit -- python -m scraper.integrations.mcp

After adding, restart Claude Desktop or reload Claude Code.
The tools will appear automatically in the tools panel.
"""

from __future__ import annotations

import json

from scraper.integrations import scrape_url, scrape_page, scrape_with_selectors, scrape_directive


def _get_mcp():
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
        return FastMCP
    except ImportError:
        raise ImportError(
            "mcp package is required to run the Scrapit MCP server.\n"
            "Install with: pip install mcp"
        )


def create_server():
    """Create and return the configured MCP server instance."""
    FastMCP = _get_mcp()
    mcp = FastMCP(
        "scrapit",
        instructions=(
            "Scrapit is a web scraping toolkit. Use these tools to fetch and extract "
            "content from web pages in real time. "
            "Start with scrape_page to get an overview of a page, "
            "then use scrape_url for the full text or scrape_with_selectors "
            "to extract specific fields."
        ),
    )

    @mcp.tool()
    def scrape_url_tool(url: str) -> str:
        """
        Fetch a web page and return its clean readable text.

        Strips scripts, styles, navigation, and footers automatically.
        Returns plain text ready to read or summarize.

        Args:
            url: The URL to fetch. Must start with http:// or https://
        """
        return scrape_url(url)

    @mcp.tool()
    def scrape_page_tool(url: str) -> str:
        """
        Fetch a web page and return structured metadata as JSON.

        Returns: title, meta description, main content text,
        list of outbound links, and word count.

        Use this when you need the page title, want to discover what links
        exist on a page, or need a structured overview before going deeper.

        Args:
            url: The URL to fetch.
        """
        page = scrape_page(url)
        page["main_content"] = page["main_content"][:4000]
        page["links"] = page["links"][:30]
        return json.dumps(page, indent=2, default=str)

    @mcp.tool()
    def scrape_with_selectors_tool(url: str, selectors: dict[str, str]) -> str:
        """
        Scrape specific fields from a web page using CSS selectors.

        Use this when you know which HTML elements contain the data you need.
        You define the field names and CSS selectors — no config file required.

        Args:
            url: The URL to scrape.
            selectors: A dict mapping field names to CSS selectors.
                Example: {"title": "h1", "price": ".price-color", "author": ".byline"}

        Returns:
            JSON with the extracted values for each field.
        """
        result = scrape_with_selectors(url, selectors)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def run_directive_tool(directive: str) -> str:
        """
        Run a pre-configured Scrapit directive by name.

        Scrapit directives are YAML files that define how to scrape a specific site,
        including CSS selectors, transforms, and validation rules.

        Use this when a directive already exists for the target site.
        Available directives: wikipedia, hn, books, github_trending

        Args:
            directive: Directive name (e.g. "wikipedia") or path to a YAML file.

        Returns:
            JSON with the structured scraped data.
        """
        result = scrape_directive(directive)
        return json.dumps(result, indent=2, default=str)

    return mcp


if __name__ == "__main__":
    server = create_server()
    server.run()
