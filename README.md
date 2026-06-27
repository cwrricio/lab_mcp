# MCP Lab Sentinel

A read-only MCP server that lets an AI assistant diagnose your lab infrastructure:
Raspberry Pi boards, Linux PCs, VMs, and any SSH-reachable host.

Ask in plain language — *"which machines are online and what OS do they run?"* — and the
assistant calls real, safe tools over SSH to answer with real data.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Protocol](https://img.shields.io/badge/MCP-Tools%20%7C%20Resources%20%7C%20Prompts-7c3aed.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen.svg)](#minimal-tests)

---

## Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Using it](#using-it)
- [Scenarios](#scenarios)
- [Use cases](#use-cases)
- [Tools, Resources and Prompts](#tools-resources-and-prompts)
- [Minimal tests](#minimal-tests)
- [Security](#security)
- [Limitations and roadmap](#limitations-and-roadmap)

## What it does

In labs with many Raspberry Pi boards and Linux PCs, you constantly check the same things
by hand: are they on, which alias to use, what OS, is SSH up, is the disk full, is the lab
ready for class. This does not scale.

Lab Sentinel exposes those checks as **safe, read-only tools** an AI can call. It reads
your existing `~/.ssh/config` as the host inventory — no separate inventory file, no
duplication. Everything it does is read-only.

## How it works

```
You (terminal)
     │  natural language
     ▼
lab-sentinel  (CLI client, OpenAI)
     │  MCP over stdio
     ▼
lab-sentinel-mcp  (the MCP server — the real product)
     │  ping + SSH (read-only, whitelisted commands)
     ▼
Raspberry Pi · Linux PC · VM · Docker
```

The **server** is the deliverable. The CLI is one way to consume it; any MCP client could
use the same server unchanged. Architecture is hexagonal (ports and adapters), so the core
logic is fully testable without touching a real machine. See
[`docs/PRD.md`](docs/PRD.md) and [`docs/adr/`](docs/adr/).

## Quick start

```bash
# 1. Install uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install the project
git clone https://github.com/cwrricio/lab_mcp.git
cd lab_mcp
uv sync

# 3. Add your OpenAI key (only the CLI needs it; the server does not)
cp .env.example .env        # then edit: OPENAI_API_KEY=sk-...

# 4. Run
uv run lab-sentinel
```

That is enough if you already SSH into your machines. **No other configuration is
required** — groups are optional (see below).

## Configuration

Three files, all optional except the SSH config you already have.

| File | Required? | Purpose |
|------|-----------|---------|
| `~/.ssh/config` | Yes (already exists) | The host inventory. Every `Host` entry is diagnosable. |
| `.env` | Only for the CLI | Holds `OPENAI_API_KEY`. Read only from this file, never the shell. Git-ignored. |
| `.sentinel.yaml` | **No** | Optional named groups (e.g. `laboratorio-109`). |

### Groups are optional

Without `.sentinel.yaml`, the system works fully: it reads every host from
`~/.ssh/config`, and hosts named `device-suffix` are auto-grouped by their suffix
(`raspi01-proxy` joins the auto-group `proxy`).

Add `.sentinel.yaml` only if you want your own named groups:

```yaml
groups:
  laboratorio-109:
    - raspi01-proxy
    - raspi02-proxy
    - proxy109
```

A host may appear in several groups. You can create any group name you like.

## Using it

### Set up an alias (recommended)

The wrapper `sentinel.sh` lets you type a short command from anywhere. Pick any name you
want (`sentinel`, `lab`, `s`, ...):

```bash
# bash
echo "alias sentinel='bash $(pwd)/sentinel.sh'" >> ~/.bashrc && source ~/.bashrc
# zsh
echo "alias sentinel='bash $(pwd)/sentinel.sh'" >> ~/.zshrc && source ~/.zshrc
```

### Interactive chat

```bash
sentinel
```

```
╭─ lab-sentinel ───────────────────────────────────────────────╮
│   MCP Lab Sentinel                                            │
│   Read-only AI diagnostics for your lab infrastructure        │
│                                                               │
│   model gpt-4o   ·   /help for tips   ·   exit to quit        │
╰───────────────────────────────────────────────────────────────╯

You › _
```

While the assistant works, a spinner shows what it is doing
(`Pinging raspi01...`, `Reading resources from raspi01...`). In-chat commands:

- `/help` — usage tips
- `/hosts` — list registered hosts instantly (no AI call, no cost)
- `exit` — quit

### See every step (verbose)

```bash
sentinel -v
```

Prints each reasoning turn and tool call:

```
─── working ───
  › Thinking
  › Listing hosts
  › Reading resources from raspi01
  › Thinking
───────────────
```

### One-shot (scripts, piping)

```bash
sentinel "Quais maquinas estao online?"
```

## Scenarios

### Scenario A — Real hardware (the primary use case)

You already have `Host` entries for your boards, including jump hosts:

```
Host proxy109
    HostName 200.132.136.134
    User emanuel
    IdentityFile ~/.ssh/id_ed25519_209

Host raspi01-proxy
    HostName localhost
    User emanuel
    Port 2400
    ProxyJump proxy109
```

Just run `sentinel`. Optionally group your real hosts in `.sentinel.yaml`.

### Scenario B — Virtual machines

Identical to real hardware — add SSH entries pointing at the VM IP/port and run `sentinel`.
No code changes.

### Scenario C — Docker demo (no hardware needed)

Spins up 3 Alpine+SSH containers that behave like lab hosts. Run from the project root:

```bash
bash docker/setup-keys.sh                                  # 1. one-time demo key
docker compose -f docker/docker-compose.yml up -d --build  # 2. start containers
cat docker/ssh_config.example >> ~/.ssh/config             # 3. register hosts (one-time)
cp docker/.sentinel.yaml.example .sentinel.yaml            # 4. optional demo group
ssh raspi01-demo "echo connected"                          # 5. verify it works
sentinel                                                    # 6. ask away
```

| Container | localhost port | SSH alias |
|-----------|----------------|-----------|
| sentinel-raspi01 | 2400 | `raspi01-demo` |
| sentinel-raspi02 | 2401 | `raspi02-demo` |
| sentinel-proxy109 | 2402 | `proxy109-demo` |

Tear down: `docker compose -f docker/docker-compose.yml down`.

A real report from this setup: [`examples/relatorio-exemplo.md`](examples/relatorio-exemplo.md).

## Use cases

For a professor or lab admin managing a fleet:

- **Before class** — *"Faca um checklist do laboratorio-109: estao todos online, SSH ok, disco abaixo de 80%?"*
- **Quick triage** — *"Quais maquinas estao offline agora?"*
- **Inventory at a glance** — *"Quais maquinas estao cadastradas e qual SO usam?"*
- **Capacity** — *"Algum host esta com disco ou memoria alta?"*
- **Config hygiene** — *"O meu ~/.ssh/config tem aliases duplicados ou sem IdentityFile?"*
- **Handover report** — *"Gere um relatorio completo do laboratorio-109."*
- **How do I connect** — *"Qual o comando para acessar o raspi01?"* → answers with `ssh raspi01`.

## Tools, Resources and Prompts

The server demonstrates all three MCP primitives.

**Tools**

| Tool | Input | Returns |
|------|-------|---------|
| `list_hosts` | `group?` | Registered hosts (no key paths) |
| `ping_host` | `name` | Reachability + latency |
| `check_ssh` | `name` | Whether SSH connects |
| `get_os_info` | `name` | OS, version, kernel, architecture |
| `get_resource_status` | `name` | Disk %, memory %, uptime, SSH service |
| `generate_report` | `filter_tag?` | Full Markdown report |
| `check_ssh_config` | — | Audit of `~/.ssh/config` |
| `suggest_fix` | `name` | Safe remediation suggestions |

**Resources:** `sentinel://hosts` (inventory), `sentinel://config` (config audit).

**Prompts:** `analise_lab(group)`, `status_geral()`, `checklist_aula(group)`.

## Minimal tests

Run the full suite: `uv run pytest` (64 tests). The essential cases:

| ID | What it checks | Expected |
|----|----------------|----------|
| TC-01 | Unknown host is rejected | `HostNotFoundError` |
| TC-02 | Offline host detected | `ping_host` returns `online: false` |
| TC-03 | SSH config parsed | aliases, ports and ProxyJump resolved correctly |
| TC-04 | **Works without `.sentinel.yaml`** | full inventory usable from `~/.ssh/config` alone |
| TC-05 | Auto-grouping | `raspi01-proxy` joins auto-group `proxy` with no config file |
| TC-06 | **Forbidden command blocked** | `rm`, `sudo`, piped/chained commands raise `SecurityError` |
| TC-07 | OS/resource parsing | raw `os-release`/`df`/`free`/`uptime` parsed into structured data |
| TC-08 | Offline host doesn't crash | `get_resource_status` returns empty status, no exception |
| TC-09 | Report completeness | always has Summary, Hosts, Alerts, Suggestions |
| TC-10 | **No key leakage** | tool output never contains `identity_file` or key paths |
| TC-11 | **Key only from `.env`** | a key in the shell env is ignored |

## Security

Secure by default (see [ADR-004](docs/adr/ADR-004-security-boundaries.md)):

- **Read-only** — nothing is ever modified on a host.
- **Allowlist** — only hosts in `~/.ssh/config` can be targeted; no arbitrary IPs.
- **Command whitelist** — a fixed set of read-only commands; anything else raises `SecurityError`.
- **No secret leakage** — key paths, private keys and `.env` values never appear in output.
- Never runs `rm`, `reboot`, `shutdown`, `sudo`, `dd`, `mkfs`, `systemctl stop/restart`, ...
- Never modifies `~/.ssh/config`.

## Limitations and roadmap

Depends on host connectivity and pre-configured SSH access. It diagnoses and suggests —
it never fixes anything automatically. For defensive and academic use only.

- [x] MVP: inventory, ping, SSH, OS info, report
- [x] Advanced: resources, SSH-config audit, alerts
- [x] DevSecOps: Docker demo, tests, docs
- [ ] Next: SSE transport (multi-client), SQLite history, run-to-run comparison
