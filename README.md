<div align="center">

# MCP Lab Sentinel

**A read-only MCP server that lets an AI assistant diagnose your lab infrastructure —
Linux PCs, VMs, and any SSH-reachable host.**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Protocol](https://img.shields.io/badge/MCP-Tools%20%7C%20Resources%20%7C%20Prompts-7c3aed.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen.svg)](#-test-cases)
[![Security](https://img.shields.io/badge/policy-read--only-success.svg)](#-security-policy)

</div>

---

## Table of Contents

1. [The Problem](#-the-problem)
2. [The Solution](#-the-solution)
3. [Architecture](#-architecture)
4. [Prerequisites](#-prerequisites)
5. [Installation](#-installation)
6. [Shell Aliases](#-shell-aliases)
7. [Configuration](#-configuration)
8. [Running the MCP Server](#-running-the-mcp-server)
9. [Running the CLI Client](#-running-the-cli-client)
10. [Docker Demo](#-docker-demo-no-hardware-needed)
11. [Available Tools](#-available-tools)
12. [Resources & Prompts](#-resources--prompts)
13. [Example Questions](#-example-questions)
14. [Test Cases](#-test-cases)
15. [Security Policy](#-security-policy)
16. [Limitations](#-limitations)
17. [Roadmap](#-roadmap)

---

## The Problem

In academic labs, IoT classrooms, and research rooms with many Linux PCs and
SSH-reachable hosts, you waste time manually checking, over and over:

- Are the devices powered on and reachable?
- Which SSH alias or IP do I use for each one?
- What OS / kernel is installed?
- Is SSH actually working?
- Is any disk almost full or memory exhausted?
- Is the lab ready for a class, experiment, or demo?

This doesn't scale beyond a handful of machines.

## The Solution

**MCP Lab Sentinel** is a local [MCP](https://modelcontextprotocol.io) server exposing
**safe, read-only diagnostic tools** to any AI client. Ask in natural language —
*"Analyze lab 109 and tell me which machines need attention"* — and the model calls real
tools to answer with real data.

It is **environment-agnostic**: it reads your existing `~/.ssh/config` as the host
inventory, so it works the same on physical hardware, VMs, or Docker containers.

The MCP server demonstrates **all three protocol primitives**:

| Primitive | What it is | In this project |
|-----------|-----------|-----------------|
| **Tools** | Functions the AI calls | `ping_host`, `check_ssh`, `get_os_info`, `generate_report`… |
| **Resources** | Readable data | `sentinel://hosts`, `sentinel://config` |
| **Prompts** | Reusable templates | `analise_lab`, `status_geral`, `checklist_aula` |

## Architecture

Hexagonal (ports & adapters) — the core logic never depends on I/O, so it is fully
testable and portable across environments.

```text
┌──────────────────┐      ┌──────────────────────────────────────────┐
│   AI Client      │      │            lab-sentinel-mcp               │
│ (CLI w/ OpenAI)  │ MCP  │                                           │
│                  │◄────►│  server.py  (Tools / Resources / Prompts) │
└──────────────────┘ stdio│       │                                   │
                          │       ▼                                   │
                          │  DiagnosticsService  (pure core)          │
                          │       │         ▲                         │
                          │  ports│         │ results                 │
                          │       ▼         │                         │
                          │  ┌───────────┬──────────┬──────────────┐  │
                          │  │ Inventory │  Ping    │ SSH (paramiko)│  │
                          │  │ (ssh cfg) │(subproc) │  whitelist    │  │
                          │  └───────────┴──────────┴──────────────┘  │
                          └───────────────────────────────────────────┘
                                               ▼
                                  Linux PC · VM · Docker container
```

## Prerequisites

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker + Docker Compose** *(only for the demo environment)*
- An **OpenAI API key** *(only for the CLI client; the MCP server itself needs none)*

## Installation

```bash
git clone https://github.com/cwrricio/lab_mcp.git
cd lab_mcp
uv sync          # creates the venv and installs everything
uv run pytest    # 64 tests should pass
```

## Shell Aliases

Add these to your `~/.bashrc` or `~/.zshrc` so you don't have to type `uv run ...` every time:

```bash
# MCP Lab Sentinel aliases
alias sentinel="uv run --project /path/to/lab_mcp lab-sentinel"
alias sentinel-mcp="uv run --project /path/to/lab_mcp lab-sentinel-mcp"
```

Replace `/path/to/lab_mcp` with the absolute path where you cloned the repo, then reload:

```bash
source ~/.bashrc   # or source ~/.zshrc
```

Now you can use:

```bash
sentinel          # opens the interactive chat client
sentinel-mcp      # starts the MCP server (stdio mode, for MCP clients)
```

## Configuration

The sentinel needs **zero configuration** beyond your existing SSH config. Two optional
files tune its behavior:

### 1. Host inventory — `~/.ssh/config` (required, already exists)

Every `Host` entry in your SSH config becomes a diagnosable host. No duplication, no extra
inventory file needed.

Example entries:

```sshconfig
Host raspi01-demo
    HostName localhost
    User demo
    Port 2400
    IdentityFile ~/.ssh/id_ed25519_sentinel_demo

Host pc-lab109
    HostName 192.168.1.10
    User student
    IdentityFile ~/.ssh/id_ed25519
```

### 2. Groups — `.sentinel.yaml` (optional)

Groups let you target a subset of hosts at once — for example, all machines in a given lab
room. Copy the template:

```bash
cp .sentinel.yaml.example .sentinel.yaml
```

```yaml
groups:
  laboratorio-109:
    - raspi01-demo
    - pc-lab109
  laboratorio-demo:
    - raspi01-demo
    - raspi02-demo
    - proxy109
```

**How groups work:**

- A host can belong to multiple groups.
- When you call `list_hosts(group="laboratorio-109")` or ask *"analyze laboratorio-109"*,
  only hosts in that group are returned and diagnosed.
- If no `.sentinel.yaml` exists, an **auto-grouping convention** applies: a host named
  `raspi01-proxy` is automatically placed in group `proxy` (the suffix after the last `-`).
- If no group is specified, all hosts in `~/.ssh/config` are returned.

### 3. OpenAI key — `.env` (only for the CLI client)

```bash
cp .env.example .env
# then edit .env:
#   OPENAI_API_KEY=sk-...
#   OPENAI_MODEL=gpt-4o
```

> The key is read **exclusively from `.env`** (never from the shell), and `.env` is
> git-ignored. It is never logged or returned by any tool.

## Running the MCP Server

The server speaks MCP over **stdio**. Run it directly to connect it to any MCP-compatible
client:

```bash
uv run lab-sentinel-mcp
# or, with the alias:
sentinel-mcp
```

The server process blocks and waits for MCP messages — it is not meant to be run
interactively in a terminal. Use it as a subprocess from an MCP client.

## Running the CLI Client

The `sentinel` command opens an **interactive chat session** powered by OpenAI GPT-4o.
The model orchestrates the MCP tools automatically based on your questions.

```bash
sentinel
# or:
uv run lab-sentinel
```

You get a prompt where you type your questions in natural language:

```
You › Quais máquinas estão online no laboratorio-demo?
You › Algum host está com disco acima de 80%?
You › Gere um relatório completo do laboratorio-demo.
You › exit
```

The client launches the MCP server as a subprocess, exposes its tools to the model, and
prints a Markdown-formatted answer to each question. Type `exit` or press `Ctrl+C` to quit.

---

## Docker Demo (no hardware needed)

Spin up a complete simulated lab in three commands:

```bash
cd docker
./setup-keys.sh                    # 1. generate a local-only demo SSH key
docker compose up -d --build       # 2. start 3 Alpine+SSH containers
                                   #    raspi01→2400  raspi02→2401  proxy109→2402
```

Then wire it into your SSH config and groups:

```bash
# 3. append the demo hosts to your SSH config (adjust IdentityFile path)
cat docker/ssh_config.example >> ~/.ssh/config

# 4. copy the demo groups
cp docker/.sentinel.yaml.example .sentinel.yaml
```

Start the interactive client and try it:

```bash
sentinel
You › Gere um relatório do laboratorio-demo
```

Tear down when finished:

```bash
cd docker && docker compose down
```

---

## Available Tools

| Tool | Input | Description |
|------|-------|-------------|
| `list_hosts` | `group?` | List registered hosts (sanitized — no key paths). Pass a group name to filter. |
| `ping_host` | `name` | Is the host reachable? Returns online status and latency in ms. |
| `check_ssh` | `name` | Attempts an SSH connection and reports success or the error. |
| `get_os_info` | `name` | Returns OS name, version, kernel, and architecture via SSH. |
| `get_resource_status` | `name` | Returns disk %, memory %, uptime, and SSH service status. |
| `get_network_info` | `name` | Returns interfaces, IPs, gateway, routes, open ports, and ARP neighbors. |
| `generate_report` | `filter_tag?` | Generates a full Markdown report for all hosts or a specific group. |
| `check_ssh_config` | — | Audits `~/.ssh/config` for duplicate aliases, missing `IdentityFile`, non-standard ports, and other common issues. |
| `suggest_fix` | `name` | Provides safe, read-only remediation suggestions based on the host's current state. |

## Resources & Prompts

**Resources** (readable context that MCP clients can fetch):
- `sentinel://hosts` — sanitized host inventory (no key paths)
- `sentinel://config` — SSH config audit summary

**Prompts** (ready-to-use templates for common tasks):
- `analise_lab(group)` — full end-to-end lab analysis: ping → SSH → OS → resources → report
- `status_geral()` — quick online/SSH status of all hosts
- `checklist_aula(group)` — pre-class readiness checklist for a lab group

## Example Questions

```text
Quais máquinas estão online no laboratorio-demo?

Analise o laboratorio-demo e diga quais máquinas precisam de atenção.

Algum host está com disco acima de 80%?

O meu ~/.ssh/config tem inconsistências?

Faça um checklist do laboratorio-demo antes da aula.

Me mostre as interfaces de rede e portas abertas do raspi01-demo.
```

## Test Cases

Run the suite with `uv run pytest` (64 tests). Key cases, in plain language:

| ID | Verifies | Expected result |
|----|----------|-----------------|
| **TC-001** | Unknown host is rejected | `ping_host("ghost")` → `HostNotFoundError` (`Host 'ghost' is not registered…`) |
| **TC-002** | Offline host detected | `ping_host` on a down host → `online: false` |
| **TC-003** | SSH config parsed | `raspi01-demo` resolves to its real IP and port |
| **TC-004** | Multi-alias blocks | Multiple hosts resolve from a single SSH config block |
| **TC-005** | Groups from `.sentinel.yaml` | `list_hosts("laboratorio-109")` returns exactly the configured members |
| **TC-006** | Auto-grouping convention | `raspi01-proxy` lands in auto-group `proxy` with no config file |
| **TC-007** | **Forbidden command blocked** | `rm -rf /`, `sudo reboot`, piped/chained commands → `SecurityError` |
| **TC-008** | OS parsing | `/etc/os-release` + `uname` → correct OS/kernel/arch |
| **TC-009** | Resource parsing | `df`/`free`/`uptime` → disk %, memory %, uptime |
| **TC-010** | Offline host doesn't crash | `get_resource_status` on a dead host → empty status, no exception |
| **TC-011** | Report sections | Report always has Summary, Hosts, Alerts, Suggestions, timestamp |
| **TC-012** | High-disk alert | Disk ≥ 80% → alert + suggestion mentioning the host |
| **TC-013** | SSH config audit | Detects duplicate alias, missing IdentityFile, non-standard port |
| **TC-014** | **No key leakage** | `list_hosts` output never contains `identity_file` or key paths |
| **TC-015** | **Key only from `.env`** | A key in the shell env is ignored; missing `.env` key → `MissingKeyError` |

## Security Policy

This project is **secure by default**:

- ✅ **Read-only**: every action only reads state
- ✅ **Host allowlist**: only hosts in `~/.ssh/config` can be targeted — no arbitrary IPs
- ✅ **Command whitelist**: a fixed set of read-only commands; anything else → `SecurityError`
- ✅ **No secret leakage**: key paths, private keys, and `.env` values never appear in output
- ✅ **No `StrictHostKeyChecking=no`** by default
- ✅ **Never** runs `rm`, `reboot`, `shutdown`, `sudo`, `dd`, `mkfs`, `systemctl stop/restart`, …
- ✅ **Never** modifies `~/.ssh/config`

## Limitations

- Depends on connectivity to the hosts.
- SSH access must be pre-configured (keys in place).
- The server never fixes problems automatically — it only diagnoses and suggests.
- Not intended for unauthorized network scanning. Defensive/academic use only.

## Roadmap

- [x] **Phase 1 — MVP**: inventory, ping, SSH, OS info, report
- [x] **Phase 2 — Advanced diagnostics**: resources, SSH-config audit, network info, alerts
- [x] **Phase 3 — DevSecOps**: Docker demo, automated tests, full docs
- [ ] **Phase 4 — Extensions**: SQLite history, dashboard, run-to-run comparison, CI

---

<div align="center">
<sub>Built as a hands-on MCP lab for networking, IoT, OS, and DevSecOps courses.</sub>
</div>
