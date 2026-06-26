# ADR-003 — Hexagonal Architecture

**Date:** 2026-06-26  
**Status:** Accepted

## Context

The server must work across multiple environments (real hardware, VMs, Docker) and remain testable without live SSH connections. A tightly coupled design would require real hosts for every test.

## Decision

Adopt hexagonal architecture (ports and adapters):

- **Core domain** (`diagnostics.py`, `report.py`): pure business logic, no I/O dependencies
- **Ports** (interfaces): `SSHClientPort`, `PingPort`, `InventoryPort`
- **Adapters**: `ParamikoSSHAdapter`, `SubprocessPingAdapter`, `SSHConfigInventoryAdapter`
- **MCP layer** (`server.py`): thin adapter between MCP protocol and core domain
- **CLI layer** (`cli.py`): thin adapter between OpenAI tool calls and MCP server

## Consequences

- Core logic is fully unit-testable with mock adapters
- Swapping SSH backends (paramiko → asyncssh) requires only a new adapter
- Docker and VM environments use identical code paths as real hardware
- Slightly more files/abstractions, justified by testability and portability requirements
