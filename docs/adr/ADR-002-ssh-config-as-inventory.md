# ADR-002 — SSH Config as Host Inventory

**Date:** 2026-06-26  
**Status:** Accepted

## Context

The server needs a host inventory to prevent arbitrary IP injection from the AI model. Options considered:
1. Custom `hosts.yaml` file
2. Read from `~/.ssh/config`
3. Environment variables

## Decision

Use `~/.ssh/config` as the primary inventory source, supplemented by an optional `.sentinel.yaml` for group definitions. Auto-grouping by `<device>-<env>` naming convention requires zero configuration.

## Consequences

- Users with existing SSH configs need no extra setup
- Works identically across real hardware, VMs, and Docker
- SSH config parsing must be robust (handle `ProxyJump`, multiple `Host` aliases per block)
- `.sentinel.yaml` is optional; its absence must not break any tool
- Sensitive fields (`IdentityFile`, `IdentityiesOnly`) are read for SSH connectivity but never exposed in tool outputs
