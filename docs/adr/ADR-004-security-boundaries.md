# ADR-004 — Security Boundaries

**Date:** 2026-06-26  
**Status:** Accepted

## Context

The MCP server executes commands on remote hosts via SSH. An AI model drives tool calls, creating a risk of prompt injection leading to destructive commands or data leakage.

## Decision

Three security layers:

1. **Host allowlist**: only hosts present in `~/.ssh/config` may be targeted; no arbitrary IPs accepted
2. **Command whitelist**: remote SSH commands are limited to a fixed set of read-only commands defined as a constant
3. **Output sanitization**: tool responses strip `IdentityFile` paths, private key content, and any value from `.env`

Forbidden commands (never executed under any circumstances):
`rm`, `reboot`, `shutdown`, `poweroff`, `mkfs`, `dd`, `chmod -R`, `chown -R`, `sudo`, `apt install`, `apt remove`, `systemctl restart`, `systemctl stop`

## Consequences

- AI model cannot inject arbitrary commands through tool arguments
- SSH key paths are invisible to the AI client
- `.env` values (including `OPENAI_API_KEY`) are never logged or returned in tool outputs
- `StrictHostKeyChecking` defaults to `accept-new` (not `no`) for first-time connections
- Tests must verify that forbidden commands raise `SecurityError`
