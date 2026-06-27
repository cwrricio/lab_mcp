# MCP Lab Sentinel

A read-only MCP server that lets an AI assistant diagnose your lab infrastructure:
Raspberry Pi boards, Linux PCs, VMs, and any SSH-reachable host.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Protocol](https://img.shields.io/badge/MCP-Tools%20%7C%20Resources%20%7C%20Prompts-7c3aed.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen.svg)](#test-cases)
[![Security](https://img.shields.io/badge/policy-read--only-success.svg)](#security-policy)

---

## Table of Contents

1. [The Problem](#the-problem)
2. [The Solution](#the-solution)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Running the MCP Server](#running-the-mcp-server)
8. [Running the CLI Client](#running-the-cli-client)
9. [Environment 1 — Real Hardware](#environment-1--real-hardware-raspberry-pi)
10. [Environment 2 — Virtual Machines](#environment-2--virtual-machines)
11. [Environment 3 — Docker Demo](#environment-3--docker-demo-no-hardware-needed)
12. [Available Tools](#available-tools)
13. [Resources and Prompts](#resources-and-prompts)
14. [Example Questions](#example-questions)
15. [Test Cases](#test-cases)
16. [Security Policy](#security-policy)
17. [Limitations](#limitations)
18. [Roadmap](#roadmap)

---

## The Problem

In academic labs, IoT classrooms, and research rooms with many Raspberry Pi boards and
Linux PCs, you waste time manually checking, over and over:

- Are the devices powered on and reachable?
- Which SSH alias or IP do I use for each one?
- What OS / kernel is installed?
- Is SSH actually working?
- Is any disk almost full or memory exhausted?
- Is the lab ready for a class, experiment, or demonstration?

This does not scale beyond a handful of machines.

## The Solution

**MCP Lab Sentinel** is a local [MCP](https://modelcontextprotocol.io) server exposing
safe, read-only diagnostic tools to any AI client. Ask in natural language and the model
calls real tools to answer with real data.

It is **environment-agnostic**: it reads your existing `~/.ssh/config` as the host
inventory, so it works the same on physical hardware, VMs, or Docker containers.

The MCP server demonstrates all three protocol primitives:

| Primitive | What it is | In this project |
|-----------|-----------|-----------------|
| Tools | Functions the AI calls | `ping_host`, `check_ssh`, `get_os_info`, `generate_report`... |
| Resources | Readable data | `sentinel://hosts`, `sentinel://config` |
| Prompts | Reusable templates | `analise_lab`, `status_geral`, `checklist_aula` |

## Architecture

Hexagonal (ports and adapters): the core logic never depends on I/O, so it is fully
testable and portable across environments.

```
+------------------+      +------------------------------------------+
|   AI Client      |      |            lab-sentinel-mcp               |
|  (CLI w/ OpenAI) | MCP  |                                           |
|                  |<---->|  server.py  (Tools / Resources / Prompts) |
+------------------+ stdio|       |                                   |
                          |       v                                   |
                          | DiagnosticsService  (pure core)           |
                          |       |          ^                        |
                          |  ports|          | results                |
                          |       v          |                        |
                          | +-----------+----------+---------------+  |
                          | | Inventory |  Ping    | SSH (paramiko)|  |
                          | | (ssh cfg) |(subproc) |  whitelist    |  |
                          | +-----------+----------+---------------+  |
                          +-------------------|-----------------------+
                                              v
                           Raspberry Pi / Linux PC / VM / Docker
```

See [`docs/PRD.md`](docs/PRD.md) and [`docs/adr/`](docs/adr/) for the full product and
architecture decision records.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker + Docker Compose *(only for the demo environment)*
- An OpenAI API key *(only for the CLI client; the MCP server itself needs none)*

## Installation

```bash
git clone https://github.com/cwrricio/lab_mcp.git
cd lab_mcp
uv sync          # creates the venv and installs all dependencies
uv run pytest    # 64 tests should pass
```

## Configuration

The sentinel needs zero extra configuration beyond your existing SSH config.
Three optional files tune its behavior:

### 1. Host inventory — `~/.ssh/config` (required, already exists)

Every `Host` entry becomes a diagnosable host. No duplication needed.

### 2. Groups — `.sentinel.yaml` (optional)

Define custom groups, or rely on the auto-grouping convention
(`raspi01-proxy` belongs to auto-group `proxy`). Copy the template:

```bash
cp .sentinel.yaml.example .sentinel.yaml
```

```yaml
groups:
  laboratorio-109:
    - raspi01-proxy
    - raspi02-proxy
    - proxy109
```

A host may belong to several groups. You can add any group name and list any SSH
alias from your `~/.ssh/config`.

### 3. OpenAI key — `.env` (only for the CLI client)

```bash
cp .env.example .env
# edit .env:
#   OPENAI_API_KEY=sk-...
#   OPENAI_MODEL=gpt-4o        # optional, defaults to gpt-4o
```

The key is read **exclusively from `.env`** (never from the shell), and `.env` is
git-ignored. It is never logged or returned by any tool.

## Running the MCP Server

The server communicates over **stdio**. It is started automatically by the CLI client.
To inspect it directly:

```bash
uv run lab-sentinel-mcp
# The process waits for MCP messages over stdin. Use Ctrl+C to exit.
```

To list all available tools without a full client:

```bash
uv run python -c "
import asyncio
from lab_sentinel.server import build_server
from lab_sentinel.factory import build_service
tools = asyncio.run(build_server(build_service()).list_tools())
for t in tools: print(t.name, '-', t.description)
"
```

## Running the CLI Client

### Step 1 — Configure the alias

The wrapper script `sentinel.sh` lets you type `sentinel` instead of
`uv run lab-sentinel`. Add the alias to your shell profile.

**Choose your alias name** — use anything you like (`sentinel`, `lab`, `s`, etc.):

```bash
# Example: alias named 'sentinel'
echo "alias sentinel='bash $(pwd)/sentinel.sh'" >> ~/.bashrc
source ~/.bashrc
```

For zsh:

```bash
echo "alias sentinel='bash $(pwd)/sentinel.sh'" >> ~/.zshrc
source ~/.zshrc
```

You can rename the alias at any time by editing that line in your shell profile.

### Step 2 — Start the interactive chat

```bash
sentinel
```

The terminal opens an interactive session:

```
 MCP Lab Sentinel
 Read-only AI diagnostics for your lab infrastructure
 Model: gpt-4o   |   Type 'exit' to quit

You: _
```

Type your question in natural language. While the model is working, a spinner
shows that the sentinel is thinking. Type `exit` or `sair` to quit.

### Verbose mode (see every tool call)

Add `-v` or `--verbose` to watch every reasoning step, tool call, and result:

```bash
sentinel -v
# or one-shot:
sentinel -v "Gere um relatorio do laboratorio-demo"
```

Output shows each turn, the tool being called, its arguments, and a preview of
the result before the final answer is composed.

### One-shot mode (for scripts and piping)

```bash
sentinel "Quais maquinas estao online?"
```

---

## Environment 1 — Real Hardware (Raspberry Pi)

If you already SSH into your boards, you are done. A typical `~/.ssh/config`
with a jump host:

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

Then:

```bash
cp .sentinel.yaml.example .sentinel.yaml   # edit groups to match your real hosts
sentinel
```

## Environment 2 — Virtual Machines

Works identically for VMs (VirtualBox, KVM, cloud). Add SSH entries pointing
at the VM IP and port:

```
Host vm-ubuntu
    HostName 192.168.56.10
    User student
    Port 22
    IdentityFile ~/.ssh/id_ed25519

Host vm-debian
    HostName 192.168.56.11
    User student
    IdentityFile ~/.ssh/id_ed25519
```

Add them to a group in `.sentinel.yaml` and run `sentinel`. No code changes.

## Environment 3 — Docker Demo (no hardware needed)

Simulates a complete lab with 3 Alpine+SSH containers running locally.
All commands run from the **project root** (`lab_mcp/`).

### Step 1 — Generate the demo SSH key (one-time)

```bash
bash docker/setup-keys.sh
```

This creates a local key at `docker/keys/sentinel_demo` (git-ignored).

### Step 2 — Start the containers

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

| Container | Port on localhost | SSH alias |
|-----------|-------------------|-----------|
| sentinel-raspi01 | 2400 | `raspi01-demo` |
| sentinel-raspi02 | 2401 | `raspi02-demo` |
| sentinel-proxy109 | 2402 | `proxy109-demo` |

### Step 3 — Register the demo hosts in your SSH config (one-time)

```bash
cat docker/ssh_config.example >> ~/.ssh/config
```

Verify connectivity:

```bash
ssh raspi01-demo "echo connected"   # should print: connected
```

### Step 4 — Create the groups file

```bash
cp docker/.sentinel.yaml.example .sentinel.yaml
```

This creates the `laboratorio-demo` group with the three containers.

### Step 5 — Start the sentinel

```bash
sentinel
# or with verbose to see every step:
sentinel -v
```

### Step 6 — Tear down when finished

```bash
docker compose -f docker/docker-compose.yml down
```

### Suggested questions to test the Docker environment

Run these one by one at the prompt:

```
Quais maquinas estao registradas no grupo laboratorio-demo?
Todas as maquinas do laboratorio-demo estao online?
Qual sistema operacional cada maquina do laboratorio-demo usa?
Gere um relatorio completo do laboratorio-demo.
Algum host do laboratorio-demo esta com disco ou memoria alta?
O meu arquivo ~/.ssh/config tem algum problema ou inconsistencia?
Faca um checklist do laboratorio-demo como se fosse antes de uma aula.
raspi01-demo esta com SSH funcionando? Qual e o uptime dele?
```

---

## Available Tools

| Tool | Input | Description |
|------|-------|-------------|
| `list_hosts` | `group?` | List registered hosts (no key paths exposed) |
| `ping_host` | `name` | Is the host reachable? Returns latency in ms |
| `check_ssh` | `name` | Does SSH connect successfully? |
| `get_os_info` | `name` | OS name, version, kernel, architecture |
| `get_resource_status` | `name` | Disk %, memory %, uptime, SSH service status |
| `generate_report` | `filter_tag?` | Full Markdown report for a group or all hosts |
| `check_ssh_config` | — | Audit `~/.ssh/config` for common misconfigurations |
| `suggest_fix` | `name` | Safe, read-only remediation suggestions |

## Resources and Prompts

Resources (readable context the model can access):

| URI | Description |
|-----|-------------|
| `sentinel://hosts` | Sanitized host inventory |
| `sentinel://config` | SSH config audit summary |

Prompts (reusable task templates):

| Name | Arguments | Description |
|------|-----------|-------------|
| `analise_lab` | `group` | Full end-to-end lab analysis |
| `status_geral` | — | Quick online/SSH status of all hosts |
| `checklist_aula` | `group` | Pre-class readiness checklist |

## Example Questions

**Inventory and connectivity**

```
Quais maquinas estao cadastradas?
Todas as maquinas do laboratorio-109 estao online?
raspi01-proxy esta respondendo? Qual a latencia?
```

**Operating system and resources**

```
Qual sistema operacional o raspi01-proxy usa?
Algum host esta com disco acima de 80%?
Como esta a memoria de todas as maquinas?
Qual o uptime do proxy109?
```

**Reports**

```
Gere um relatorio completo do laboratorio-109.
Faca um checklist do laboratorio-demo como se fosse antes de uma aula.
```

**Diagnosis and suggestions**

```
O meu arquivo ~/.ssh/config tem inconsistencias ou problemas?
O que devo fazer se o raspi02-proxy nao responde?
Alguma maquina precisa de atencao agora?
```

## Test Cases

Run the full suite: `uv run pytest` (64 tests).

| ID | Verifies | Expected result |
|----|----------|-----------------|
| TC-001 | Unknown host is rejected | `HostNotFoundError: Host 'ghost' is not registered` |
| TC-002 | Offline host detected | `ping_host` returns `online: false` |
| TC-003 | SSH config parsed correctly | `proxy109` resolves to correct IP, port, ProxyJump |
| TC-004 | Multi-alias blocks | `pc209` and `proxy209` both resolve from one config block |
| TC-005 | Groups from `.sentinel.yaml` | `list_hosts("laboratorio-109")` returns exactly 3 members |
| TC-006 | Auto-grouping by convention | `raspi01-proxy` lands in auto-group `proxy` with no config file |
| TC-007 | Forbidden command blocked | `rm -rf /`, `sudo reboot`, piped commands raise `SecurityError` |
| TC-008 | OS output parsed | `/etc/os-release` + `uname` returns correct OS/kernel/arch |
| TC-009 | Resource metrics parsed | `df`/`free`/`uptime` returns disk %, memory %, uptime |
| TC-010 | Offline host handled gracefully | `get_resource_status` on dead host returns empty status, no crash |
| TC-011 | Report has all sections | Output always contains Summary, Hosts, Alerts, Suggestions, timestamp |
| TC-012 | High-disk alert | Disk >= 80% generates alert and suggestion for that host |
| TC-013 | SSH config audited | Detects duplicate alias, missing IdentityFile, non-standard port |
| TC-014 | No key path leakage | `list_hosts` output never contains `identity_file` or key paths |
| TC-015 | Key only from `.env` | Shell env key ignored; missing `.env` key raises `MissingKeyError` |

## Security Policy

Secure by default (see [ADR-004](docs/adr/ADR-004-security-boundaries.md)):

- **Read-only**: every action only reads state, never modifies anything
- **Host allowlist**: only hosts in `~/.ssh/config` can be targeted — no arbitrary IPs
- **Command whitelist**: fixed set of read-only commands; anything else raises `SecurityError`
- **No secret leakage**: key paths, private keys, and `.env` values never appear in output
- **No `StrictHostKeyChecking=no`** — defaults to `accept-new` for first-time connections
- Never runs: `rm`, `reboot`, `shutdown`, `poweroff`, `sudo`, `dd`, `mkfs`, `apt install`,
  `apt remove`, `systemctl restart`, `systemctl stop`, `chmod -R`, `chown -R`
- Never modifies `~/.ssh/config`

## Limitations

- Depends on connectivity to the hosts.
- SSH access must be pre-configured (keys already in place).
- The server never fixes problems automatically — it only diagnoses and suggests.
- Not intended for unauthorized network scanning. Defensive and academic use only.

## Roadmap

- [x] Phase 1 — MVP: inventory, ping, SSH, OS info, report
- [x] Phase 2 — Advanced diagnostics: resources, SSH-config audit, alerts
- [x] Phase 3 — DevSecOps: Docker, automated tests, full docs
- [ ] Phase 4 — Extensions: SQLite history, dashboard, run-to-run comparison, CI
