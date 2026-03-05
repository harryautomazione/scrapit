"""
Native Anthropic SDK integration for Scrapit.

Use Scrapit tools directly in any application built with the Anthropic Python SDK,
without needing LangChain or any other framework.

Usage:

    import anthropic
    from scraper.integrations.anthropic import as_anthropic_tools, handle_tool_call

    client = anthropic.Anthropic()
    tools  = as_anthropic_tools()

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        tools=tools,
        messages=[{"role": "user", "content": "What does the Wikipedia article on Python say?"}],
    )

    # Process tool calls in the response
    for block in response.content:
        if block.type == "tool_use":
            result = handle_tool_call(block.name, block.input)
            print(result)

Full agentic loop:

    from scraper.integrations.anthropic import ScrapitAnthropicAgent

    agent = ScrapitAnthropicAgent(model="claude-opus-4-6")
    result = agent.run("Scrape the top 5 links from Hacker News and summarize each one.")
    print(result)
"""

from __future__ import annotations

import json
from typing import Any

from scraper.integrations import scrape_url, scrape_page, scrape_with_selectors, scrape_directive


# ── tool definitions ──────────────────────────────────────────────────────────

_TOOLS: list[dict] = [
    {
        "name": "scrape_url",
        "description": (
            "Fetch a web page and return its clean readable text content. "
            "Use this to read articles, documentation, blog posts, or any static web page. "
            "Strips navigation, scripts, and footers automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to scrape. Must start with http:// or https://",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "scrape_page",
        "description": (
            "Fetch a web page and return structured metadata: "
            "title, meta description, main content, outbound links, and word count. "
            "Prefer this when you need the page title, want to discover links, "
            "or need a structured summary of the page."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch.",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "scrape_with_selectors",
        "description": (
            "Scrape specific fields from a web page using CSS selectors. "
            "Use this when you know which HTML elements contain the data you need. "
            "You define the field names and selectors — no config file needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to scrape.",
                },
                "selectors": {
                    "type": "object",
                    "description": (
                        "Mapping of field_name to CSS selector. "
                        'Example: {"title": "h1", "price": ".price-color", "author": ".byline"}'
                    ),
                    "additionalProperties": {"type": "string"},
                },
                "all_matches": {
                    "type": "object",
                    "description": (
                        "Optional. Set a field to true to return all matches as a list "
                        "instead of just the first. "
                        'Example: {"tags": true}'
                    ),
                    "additionalProperties": {"type": "boolean"},
                },
            },
            "required": ["url", "selectors"],
        },
    },
    {
        "name": "scrape_directive",
        "description": (
            "Run a pre-configured Scrapit directive to scrape a website. "
            "Use this when a directive YAML has already been set up for the target site. "
            "Returns structured JSON with the fields defined in the directive."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directive": {
                    "type": "string",
                    "description": "Directive name (e.g. 'wikipedia', 'hn') or path to YAML file.",
                },
            },
            "required": ["directive"],
        },
    },
]


def as_anthropic_tools() -> list[dict]:
    """Return all Scrapit tools in Anthropic API format."""
    return _TOOLS


def handle_tool_call(tool_name: str, tool_input: dict[str, Any]) -> str:
    """
    Execute a Scrapit tool call from an Anthropic agent response.

    Args:
        tool_name: The tool name from block.name.
        tool_input: The tool input from block.input.

    Returns:
        String result to send back as a tool_result message.
    """
    try:
        if tool_name == "scrape_url":
            return scrape_url(tool_input["url"])

        elif tool_name == "scrape_page":
            page = scrape_page(tool_input["url"])
            page["main_content"] = page["main_content"][:4000]
            page["links"] = page["links"][:30]
            return json.dumps(page, indent=2, default=str)

        elif tool_name == "scrape_with_selectors":
            result = scrape_with_selectors(
                tool_input["url"],
                tool_input["selectors"],
                all_matches=tool_input.get("all_matches"),
            )
            return json.dumps(result, indent=2, default=str)

        elif tool_name == "scrape_directive":
            result = scrape_directive(tool_input["directive"])
            return json.dumps(result, indent=2, default=str)

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Tool '{tool_name}' failed: {e}"


# ── ScrapitAnthropicAgent ─────────────────────────────────────────────────────

class ScrapitAnthropicAgent:
    """
    A simple agentic loop using the Anthropic SDK and all Scrapit tools.

    The agent automatically handles tool calls until it produces a final answer.

    Usage:

        from scraper.integrations.anthropic import ScrapitAnthropicAgent

        agent = ScrapitAnthropicAgent(model="claude-opus-4-6")
        answer = agent.run("What are the top stories on Hacker News right now?")
        print(answer)
    """

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        max_iterations: int = 10,
        system: str | None = None,
    ):
        try:
            import anthropic as _anthropic  # type: ignore
            self._client = _anthropic.Anthropic()
        except ImportError:
            raise ImportError(
                "anthropic SDK is required. Install with: pip install anthropic"
            )
        self.model = model
        self.max_iterations = max_iterations
        self.system = system or (
            "You are a helpful research assistant with access to web scraping tools. "
            "Use the tools to fetch information from the web when needed. "
            "Always cite the URLs you scraped."
        )

    def run(self, prompt: str) -> str:
        """
        Run the agent on a prompt and return the final text response.

        The agent will call Scrapit tools as needed to answer the question.
        """
        import anthropic  # type: ignore

        messages = [{"role": "user", "content": prompt}]
        tools = as_anthropic_tools()

        for _ in range(self.max_iterations):
            response = self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system,
                tools=tools,
                messages=messages,
            )

            # Collect assistant message
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Final answer — extract text
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = handle_tool_call(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "user", "content": tool_results})

        return "Max iterations reached."
