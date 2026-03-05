"""
OpenAI function calling integration for Scrapit.

Use Scrapit tools directly with the OpenAI SDK (gpt-4o, gpt-4-turbo, etc.)
without needing LangChain or any other framework.

Usage:

    from openai import OpenAI
    from scraper.integrations.openai import as_openai_functions, handle_function_call

    client = OpenAI()
    tools  = as_openai_functions()

    response = client.chat.completions.create(
        model="gpt-4o",
        tools=tools,
        messages=[{"role": "user", "content": "What are the top posts on Hacker News?"}],
    )

    message = response.choices[0].message
    if message.tool_calls:
        for call in message.tool_calls:
            result = handle_function_call(call.function.name, call.function.arguments)
            print(result)

Full agentic loop:

    from scraper.integrations.openai import ScrapitOpenAIAgent

    agent = ScrapitOpenAIAgent(model="gpt-4o")
    result = agent.run("Summarize the Wikipedia article about the Python programming language.")
    print(result)
"""

from __future__ import annotations

import json
from typing import Any

from scraper.integrations import scrape_url, scrape_page, scrape_with_selectors, scrape_directive


# ── tool definitions ──────────────────────────────────────────────────────────

_FUNCTIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "scrape_url",
            "description": (
                "Fetch a web page and return its clean readable text. "
                "Strips navigation, scripts, and footers. "
                "Use for reading articles, docs, or any static page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch (http:// or https://).",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_page",
            "description": (
                "Fetch a web page and return structured metadata: "
                "title, description, main_content, links, word_count. "
                "Use when you need the title, want to discover links, "
                "or need a structured overview of the page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_with_selectors",
            "description": (
                "Scrape specific fields from a web page using CSS selectors. "
                "Use when you know which HTML elements contain the data you need."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape.",
                    },
                    "selectors": {
                        "type": "object",
                        "description": (
                            'Field name → CSS selector mapping. '
                            'Example: {"title": "h1", "price": ".price-color"}'
                        ),
                        "additionalProperties": {"type": "string"},
                    },
                    "all_matches": {
                        "type": "object",
                        "description": (
                            "Set field to true to return all matches as a list. "
                            'Example: {"tags": true}'
                        ),
                        "additionalProperties": {"type": "boolean"},
                    },
                },
                "required": ["url", "selectors"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_directive",
            "description": (
                "Run a pre-configured Scrapit directive. "
                "Use when a YAML directive has already been set up for the target site."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "directive": {
                        "type": "string",
                        "description": "Directive name (e.g. 'wikipedia') or path to YAML file.",
                    },
                },
                "required": ["directive"],
            },
        },
    },
]


def as_openai_functions() -> list[dict]:
    """Return all Scrapit tools in OpenAI function calling format."""
    return _FUNCTIONS


def handle_function_call(function_name: str, arguments: str | dict[str, Any]) -> str:
    """
    Execute a Scrapit tool call from an OpenAI agent response.

    Args:
        function_name: The function name from call.function.name.
        arguments: JSON string or dict from call.function.arguments.

    Returns:
        String result to send back as a tool message.
    """
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments

        if function_name == "scrape_url":
            return scrape_url(args["url"])

        elif function_name == "scrape_page":
            page = scrape_page(args["url"])
            page["main_content"] = page["main_content"][:4000]
            page["links"] = page["links"][:30]
            return json.dumps(page, indent=2, default=str)

        elif function_name == "scrape_with_selectors":
            result = scrape_with_selectors(
                args["url"],
                args["selectors"],
                all_matches=args.get("all_matches"),
            )
            return json.dumps(result, indent=2, default=str)

        elif function_name == "scrape_directive":
            result = scrape_directive(args["directive"])
            return json.dumps(result, indent=2, default=str)

        else:
            return f"Unknown function: {function_name}"

    except Exception as e:
        return f"Function '{function_name}' failed: {e}"


# ── ScrapitOpenAIAgent ────────────────────────────────────────────────────────

class ScrapitOpenAIAgent:
    """
    A simple agentic loop using the OpenAI SDK and all Scrapit tools.

    The agent automatically handles function calls until it produces a final answer.

    Usage:

        from scraper.integrations.openai import ScrapitOpenAIAgent

        agent = ScrapitOpenAIAgent(model="gpt-4o")
        answer = agent.run("What are the top posts on Hacker News right now?")
        print(answer)
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        max_iterations: int = 10,
        system: str | None = None,
    ):
        try:
            from openai import OpenAI  # type: ignore
            self._client = OpenAI()
        except ImportError:
            raise ImportError(
                "openai SDK is required. Install with: pip install openai"
            )
        self.model = model
        self.max_iterations = max_iterations
        self.system = system or (
            "You are a helpful research assistant with access to web scraping tools. "
            "Use the tools to fetch real-time information from the web when needed. "
            "Always cite the URLs you scraped."
        )

    def run(self, prompt: str) -> str:
        """Run the agent on a prompt and return the final text response."""
        messages = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": prompt},
        ]
        tools = as_openai_functions()

        for _ in range(self.max_iterations):
            response = self._client.chat.completions.create(
                model=self.model,
                tools=tools,
                messages=messages,
            )

            message = response.choices[0].message
            messages.append(message)

            if not message.tool_calls:
                return message.content or ""

            for call in message.tool_calls:
                result = handle_function_call(call.function.name, call.function.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                })

        return "Max iterations reached."
