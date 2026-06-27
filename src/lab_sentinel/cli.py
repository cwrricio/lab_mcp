"""Terminal client that drives the MCP server with OpenAI.

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
from typing import Callable

# Silence library INFO logs (paramiko auth, mcp requests) so the UI stays clean.
for _noisy in ("paramiko", "mcp", "asyncio"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

from dotenv import dotenv_values
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

DEFAULT_MODEL = "gpt-4o"
DEFAULT_ENV_FILE = ".env"
MAX_REASONING_TURNS = 10

_THEME = Theme(
    {
        "title": "bold cyan",
        "subtle": "dim white",
        "prompt": "bold green",
        "tool": "yellow",
        "args": "dim yellow",
        "step": "bold blue",
        "error": "bold red",
        "ok": "green",
    }
)
console = Console(theme=_THEME, highlight=False)

# Human-readable hints shown in the spinner while a tool runs.
_TOOL_LABELS = {
    "list_hosts": "Listing hosts",
    "ping_host": "Pinging",
    "check_ssh": "Checking SSH on",
    "get_os_info": "Reading OS info from",
    "get_resource_status": "Reading resources from",
    "generate_report": "Building report",
    "check_ssh_config": "Auditing SSH config",
    "suggest_fix": "Analyzing",
}

SYSTEM_PROMPT = (
    "You are MCP Lab Sentinel, a read-only infrastructure diagnostics assistant. "
    "Use the provided tools to answer questions about lab hosts. Only act on hosts "
    "returned by list_hosts. Never invent hosts or data. Answer in clear Markdown, "
    "in the same language the user used.\n\n"
    "When telling the user how to SSH into a host, always use the SSH alias from the "
    "inventory (e.g. `ssh raspi01`), never the raw `user@host -p port` form, because "
    "the alias already carries the correct key, port and ProxyJump settings."
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


# -- MCP <-> OpenAI bridge -----------------------------------------------

def _mcp_tools_to_openai(tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


def _tool_label(name: str, args: dict) -> str:
    """A short, friendly progress label for the spinner."""
    base = _TOOL_LABELS.get(name, name)
    target = args.get("name") or args.get("group") or args.get("filter_tag")
    return f"{base} {target}".strip() if target else base


async def _run_query(
    query: str,
    config: OpenAIConfig,
    on_event: Callable[[str], None] | None = None,
) -> str:
    """Start the MCP server over stdio and let the model orchestrate the tools.

    ``on_event(message)`` is called with a human-readable progress string before
    each tool call, so the caller can update a spinner.
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from openai import OpenAI

    client = OpenAI(api_key=config.api_key)
    server_params = StdioServerParameters(
        command=sys.executable, args=["-m", "lab_sentinel.server"], env=os.environ.copy()
    )

    def emit(message: str) -> None:
        if on_event:
            on_event(message)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_list = (await session.list_tools()).tools
            openai_tools = _mcp_tools_to_openai(tool_list)

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ]

            for _turn in range(MAX_REASONING_TURNS):
                emit("Thinking")
                response = client.chat.completions.create(
                    model=config.model, messages=messages, tools=openai_tools
                )
                msg = response.choices[0].message
                messages.append(msg.model_dump(exclude_none=True))

                if not msg.tool_calls:
                    return msg.content or ""

                for call in msg.tool_calls:
                    args = json.loads(call.function.arguments or "{}")
                    emit(_tool_label(call.function.name, args))
                    result = await session.call_tool(call.function.name, args)
                    payload = "\n".join(
                        block.text for block in result.content if hasattr(block, "text")
                    )
                    messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": payload}
                    )

            return "Reached the maximum number of reasoning steps without a final answer."


# -- presentation --------------------------------------------------------

def _banner(model: str) -> Panel:
    body = Group(
        Text("MCP Lab Sentinel", style="title"),
        Text("Read-only AI diagnostics for your lab infrastructure", style="subtle"),
        Text(""),
        Text(f"model {model}   ·   /help for tips   ·   exit to quit", style="subtle"),
    )
    return Panel(body, border_style="cyan", padding=(1, 3), title="lab-sentinel", title_align="left")


_HELP = """\
**How to ask**

Just type a question in plain language. Examples:

- Quais maquinas estao online?
- Qual o sistema operacional do raspi01?
- Gere um relatorio completo do laboratorio.
- Algum host esta com disco acima de 80%?
- O meu ~/.ssh/config tem algum problema?

**Commands**

- `/help`   show this help
- `/hosts`  list registered hosts (no AI call)
- `exit`    quit

**Flags**

- `-v` / `--verbose`  show every tool call and result
"""


def _print_hosts() -> None:
    """List the inventory directly, with no AI call (fast, free)."""
    from .factory import build_service

    hosts = build_service().list_hosts()
    if not hosts:
        console.print("[error]No hosts found in ~/.ssh/config.[/error]")
        return
    table = Table(border_style="dim cyan", show_lines=False)
    table.add_column("Host", style="tool", no_wrap=True)
    table.add_column("Address")
    table.add_column("User")
    table.add_column("Port", justify="right")
    table.add_column("Groups", style="subtle")
    for h in hosts:
        table.add_row(h.name, h.host, h.user, str(h.port), ", ".join(h.tags) or "-")
    console.print(table)


def _answer(query: str, config: OpenAIConfig, verbose: bool) -> None:
    """Run one query and render the answer, with progress feedback."""
    if verbose:
        console.print(Rule("working", style="dim cyan"))
        answer = asyncio.run(
            _run_query(query, config, on_event=lambda m: console.print(f"  [step]›[/step] {m}"))
        )
        console.print(Rule(style="dim cyan"))
    else:
        with console.status("[subtle]Starting...[/subtle]", spinner="dots", spinner_style="cyan") as status:
            answer = asyncio.run(
                _run_query(query, config, on_event=lambda m: status.update(f"[subtle]{m}...[/subtle]"))
            )
    console.print(Markdown(answer))


def _chat_loop(config: OpenAIConfig, verbose: bool) -> None:
    console.print(_banner(config.model))
    console.print()
    while True:
        try:
            query = console.input("[prompt]You ›[/prompt] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[subtle]Bye.[/subtle]")
            break
        if not query:
            continue
        low = query.lower()
        if low in {"exit", "quit", "sair"}:
            console.print("[subtle]Bye.[/subtle]")
            break
        if low in {"/help", "help", "?"}:
            console.print(Markdown(_HELP))
            continue
        if low in {"/hosts", "hosts"}:
            _print_hosts()
            continue
        console.print()
        _answer(query, config, verbose)
        console.print()


def main() -> None:
    flags = {"--verbose", "-v"}
    verbose = any(a in flags for a in sys.argv[1:])
    args = [a for a in sys.argv[1:] if a not in flags]

    env_file = os.getenv("SENTINEL_ENV_FILE", DEFAULT_ENV_FILE)
    try:
        config = load_openai_config(env_file)
    except MissingKeyError as exc:
        console.print(f"[error]Error:[/error] {exc}")
        sys.exit(1)

    if args:
        _answer(" ".join(args), config, verbose)
    else:
        _chat_loop(config, verbose)


if __name__ == "__main__":
    main()
