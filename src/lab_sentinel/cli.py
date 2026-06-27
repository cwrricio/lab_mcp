"""Terminal CLI client that drives the MCP server with OpenAI GPT-4o.

The MCP server is the product; this client is a demonstration of consuming it.
The OpenAI API key is read EXCLUSIVELY from a local ``.env`` file (never from the
shell environment), so it cannot be leaked through the process environment.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

# Suppress noisy INFO logs from paramiko and mcp unless explicitly running verbose.
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

DEFAULT_MODEL = "gpt-4o"
DEFAULT_ENV_FILE = ".env"

_THEME = Theme(
    {
        "banner.title": "bold cyan",
        "banner.sub": "dim white",
        "prompt.label": "bold green",
        "tool.name": "bold yellow",
        "tool.args": "dim yellow",
        "tool.result": "dim cyan",
        "step.header": "bold blue",
        "error": "bold red",
        "info": "dim white",
    }
)

console = Console(theme=_THEME, highlight=False)

SYSTEM_PROMPT = (
    "You are MCP Lab Sentinel, a read-only infrastructure diagnostics assistant. "
    "Use the provided tools to answer questions about lab hosts. Only act on hosts "
    "returned by list_hosts. Never invent hosts or data. Summarize findings in clear "
    "Markdown, in the language the user used.\n\n"
    "When telling the user how to SSH into a host, always use the SSH alias from the "
    "inventory (e.g. `ssh raspi01-demo`), never the raw `user@host -p port` form, "
    "because the alias already carries the correct key, port and ProxyJump settings."
)


class MissingKeyError(Exception):
    """Raised when no OpenAI API key is found in the .env file."""

    def __init__(self) -> None:
        super().__init__(
            "OPENAI_API_KEY not found. Copy .env.example to .env and set your key. "
            "The key is read only from the .env file, never from the shell."
        )


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str = DEFAULT_MODEL


def load_openai_config(env_path: str | os.PathLike[str] = DEFAULT_ENV_FILE) -> OpenAIConfig:
    """Load OpenAI config strictly from the given ``.env`` file."""
    path = Path(os.path.expanduser(str(env_path)))
    if not path.is_file():
        raise MissingKeyError()
    values = dotenv_values(path)
    api_key = (values.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise MissingKeyError()
    model = (values.get("OPENAI_MODEL") or DEFAULT_MODEL).strip()
    return OpenAIConfig(api_key=api_key, model=model)


# -- MCP tool bridging ---------------------------------------------------

def _mcp_tools_to_openai(tools) -> list[dict]:
    specs = []
    for tool in tools:
        specs.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                },
            }
        )
    return specs


async def _run_query(query: str, config: OpenAIConfig, verbose: bool = False) -> str:
    """Start the MCP server over stdio and let GPT-4o orchestrate the tools."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from openai import OpenAI

    client = OpenAI(api_key=config.api_key)
    server_params = StdioServerParameters(
        command=sys.executable, args=["-m", "lab_sentinel.server"], env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_list = (await session.list_tools()).tools
            openai_tools = _mcp_tools_to_openai(tool_list)

            if verbose:
                _print_tools_table(tool_list)

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ]

            for turn in range(10):
                if verbose:
                    console.print(
                        f"\n[step.header]-- Reasoning turn {turn + 1} --[/step.header]"
                    )

                response = client.chat.completions.create(
                    model=config.model, messages=messages, tools=openai_tools
                )
                msg = response.choices[0].message
                messages.append(msg.model_dump(exclude_none=True))

                if not msg.tool_calls:
                    return msg.content or ""

                for call in msg.tool_calls:
                    args = json.loads(call.function.arguments or "{}")
                    if verbose:
                        console.print(
                            f"  [tool.name]calling[/tool.name] {call.function.name}"
                            f"  [tool.args]{json.dumps(args)}[/tool.args]"
                        )
                    result = await session.call_tool(call.function.name, args)
                    payload = "\n".join(
                        block.text for block in result.content if hasattr(block, "text")
                    )
                    if verbose:
                        preview = payload[:120].replace("\n", " ")
                        console.print(f"  [tool.result]=> {preview}...[/tool.result]")
                    messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": payload}
                    )

            return "Reached the maximum number of reasoning steps without a final answer."


def _print_tools_table(tools) -> None:
    table = Table(title="Available Tools", show_lines=True, border_style="dim cyan")
    table.add_column("Tool", style="bold yellow", no_wrap=True)
    table.add_column("Description", style="white")
    for t in tools:
        table.add_row(t.name, t.description or "")
    console.print(table)


def _print_banner(model: str) -> None:
    content = Text.assemble(
        ("MCP Lab Sentinel\n", "banner.title"),
        ("Read-only AI diagnostics for your lab infrastructure\n", "banner.sub"),
        (f"Model: {model}   |   Type 'exit' to quit", "info"),
    )
    console.print(Panel(content, border_style="cyan", padding=(0, 2)))


def _chat_loop(config: OpenAIConfig, verbose: bool) -> None:
    _print_banner(config.model)
    console.print()

    while True:
        try:
            query = console.input("[prompt.label]You:[/prompt.label] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[info]Exiting.[/info]")
            break
        if not query:
            continue
        if query.lower() in {"exit", "quit", "sair"}:
            console.print("[info]Exiting.[/info]")
            break

        console.print()
        if verbose:
            answer = asyncio.run(_run_query(query, config, verbose=True))
            console.print(Rule(style="dim cyan"))
        else:
            with Status(
                "[info]Thinking...[/info]",
                spinner="dots",
                spinner_style="cyan",
                console=console,
            ):
                answer = asyncio.run(_run_query(query, config, verbose=False))

        console.print(Markdown(answer))
        console.print()


def main() -> None:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--verbose", "-v")]

    env_file = os.getenv("SENTINEL_ENV_FILE", DEFAULT_ENV_FILE)
    try:
        config = load_openai_config(env_file)
    except MissingKeyError as exc:
        console.print(f"[error]Error:[/error] {exc}")
        sys.exit(1)

    if args:
        query = " ".join(args)
        if verbose:
            answer = asyncio.run(_run_query(query, config, verbose=True))
            console.print(Rule(style="dim cyan"))
        else:
            with Status(
                "[info]Thinking...[/info]",
                spinner="dots",
                spinner_style="cyan",
                console=console,
            ):
                answer = asyncio.run(_run_query(query, config, verbose=False))
        console.print(Markdown(answer))
    else:
        _chat_loop(config, verbose)


if __name__ == "__main__":
    main()
