# ADR-005 — OpenAI GPT-4o as CLI Client

**Date:** 2026-06-26  
**Status:** Accepted

## Context

The MCP server needs a demonstration client. Options considered:
1. Claude Desktop (no code required, but not terminal-native)
2. Custom CLI with OpenAI SDK
3. No client (server only)

## Decision

Build a minimal CLI client (`cli.py`) using OpenAI GPT-4o with tool calling. The client:
- Reads `OPENAI_API_KEY` exclusively from a `.env` file (never from shell env or hardcoded)
- Starts the MCP server as a subprocess and communicates via stdio transport
- Accepts a natural language query as a CLI argument
- Prints a Markdown report to stdout

## Consequences

- Users must have an OpenAI account and API key
- `.env` must be in `.gitignore` (enforced)
- The CLI is a demo artifact; the MCP server has no dependency on OpenAI
- Model choice (gpt-4o) can be overridden via `OPENAI_MODEL` in `.env`
