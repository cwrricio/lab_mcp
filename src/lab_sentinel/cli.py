"""Terminal CLI client that drives the MCP server with OpenAI GPT-4o.

The MCP server is the product; this client is a demonstration of consuming it.
The OpenAI API key is read EXCLUSIVELY from a local ``.env`` file (never from the
shell environment), so it cannot be leaked through the process environment.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_MODEL = "gpt-4o"
DEFAULT_ENV_FILE = ".env"

SYSTEM_PROMPT = (
    "You are MCP Lab Sentinel, a read-only infrastructure diagnostics assistant. "
    "Use the provided tools to answer questions about lab hosts. Only act on hosts "
    "returned by list_hosts. Never invent hosts or data. Summarize findings in clear "
    "Markdown, in the language the user used."
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
    values = dotenv_values(path)  # reads the file only, ignores os.environ
    api_key = (values.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise MissingKeyError()
    model = (values.get("OPENAI_MODEL") or DEFAULT_MODEL).strip()
    return OpenAIConfig(api_key=api_key, model=model)


# -- MCP tool bridging ---------------------------------------------------


def _mcp_tools_to_openai(tools) -> list[dict]:
    """Convert MCP tool definitions into OpenAI function-tool specs."""
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


async def _run_query(query: str, config: OpenAIConfig) -> str:
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

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ]

            for _ in range(10):  # cap agentic turns
                response = client.chat.completions.create(
                    model=config.model, messages=messages, tools=openai_tools
                )
                msg = response.choices[0].message
                messages.append(msg.model_dump(exclude_none=True))

                if not msg.tool_calls:
                    return msg.content or ""

                for call in msg.tool_calls:
                    args = json.loads(call.function.arguments or "{}")
                    result = await session.call_tool(call.function.name, args)
                    payload = "\n".join(
                        block.text for block in result.content if hasattr(block, "text")
                    )
                    messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": payload}
                    )

            return "Reached the maximum number of reasoning steps without a final answer."


_BANNER = """
╔══════════════════════════════════════════════════════╗
║           🛰️  MCP Lab Sentinel — Chat Mode           ║
║  Ask anything about your lab. Type 'exit' to quit.   ║
╚══════════════════════════════════════════════════════╝
"""


def _chat_loop(config: OpenAIConfig) -> None:
    print(_BANNER)
    while True:
        try:
            query = input("🔍 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not query:
            continue
        if query.lower() in {"exit", "quit", "sair"}:
            print("Bye!")
            break
        print()
        answer = asyncio.run(_run_query(query, config))
        print(answer)
        print()


def main() -> None:
    env_file = os.getenv("SENTINEL_ENV_FILE", DEFAULT_ENV_FILE)
    try:
        config = load_openai_config(env_file)
    except MissingKeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 1:
        # One-shot mode: pass query directly (useful for scripts/piping)
        query = " ".join(sys.argv[1:])
        print(asyncio.run(_run_query(query, config)))
    else:
        # Interactive chat mode
        _chat_loop(config)


if __name__ == "__main__":
    main()
