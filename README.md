<div align="center">

# MCP Lab Sentinel

**A read-only MCP server that lets an AI assistant diagnose your lab infrastructure —
Raspberry Pi boards, Linux PCs, and any SSH-reachable host.**

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
6. [Configuration](#-configuration)
7. [Running the MCP Server](#-running-the-mcp-server)
8. [Running the CLI Client](#-running-the-cli-client)
9. [Environment 1 — Real Hardware](#-environment-1--real-hardware-raspberry-pi)
10. [Environment 2 — Virtual Machines](#-environment-2--virtual-machines)
11. [Environment 3 — Docker Demo](#-environment-3--docker-demo-no-hardware-needed)
12. [Available Tools](#-available-tools)
13. [Resources & Prompts](#-resources--prompts)
14. [Example Questions](#-example-questions)
15. [Test Cases](#-test-cases)
16. [Security Policy](#-security-policy)
17. [Limitations](#-limitations)
18. [Roadmap](#-roadmap)

---

## The Problem

In academic labs, IoT classrooms, and research rooms with many Raspberry Pi boards and
Linux PCs, you waste time manually checking, over and over:

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
| 🔧 **Tools** | Functions the AI calls | `ping_host`, `check_ssh`, `get_os_info`, `generate_report`… |
| 📄 **Resources** | Readable data | `sentinel://hosts`, `sentinel://config` |
| 💬 **Prompts** | Reusable templates | `analise_lab`, `status_geral`, `checklist_aula` |

##  Architecture

Hexagonal (ports & adapters) — the core logic never depends on I/O, so it is fully
testable and portable across environments.

```text
┌──────────────────┐      ┌──────────────────────────────────────────┐
│   AI Client      │      │            lab-sentinel-mcp                │
│ (Claude Desktop, │ MCP  │                                            │
│  CLI w/ OpenAI)  │◄────►│   server.py   (Tools / Resources / Prompts)│
└──────────────────┘ stdio│        │                                   │
                          │        ▼                                   │
                          │  DiagnosticsService  (pure core)           │
                          │        │         ▲                         │
                          │   ports │         │ results                │
                          │        ▼         │                         │
                          │  ┌───────────┬──────────┬───────────────┐  │
                          │  │ Inventory │  Ping    │  SSH (paramiko)│  │
                          │  │ (ssh cfg) │(subproc) │  whitelist     │  │
                          │  └───────────┴──────────┴───────────────┘  │
                          └────────────────────│───────────────────────┘
                                               ▼
                            Raspberry Pi · Linux PC · VM · Docker
```

See [`docs/PRD.md`](docs/PRD.md) and [`docs/adr/`](docs/adr/) for the full product and
architecture decision records.

## Prerequisites

- **Python 3.11+**
- **[uv](https://github.com/astral-ch/uv)** — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker + Docker Compose** *(only for the demo environment)*
- An **OpenAI API key** *(only for the CLI client; the server itself needs none)*

## Installation

```bash
git clone https://github.com/cwrricio/lab_mcp.git
cd lab_mcp
uv sync          # creates the venv and installs everything
uv run pytest    # 64 tests should pass
```

## Configuration

The sentinel needs **zero configuration** beyond your existing SSH config. Three optional
files tune its behavior:

### 1. Host inventory — `~/.ssh/config` (required, already exists)

Every `Host` entry becomes a diagnosable host. No duplication, no extra inventory file.

### 2. Groups — `.sentinel.yaml` (optional)

Create custom groups, or rely on the auto-grouping convention (`raspi01-proxy` → group
`proxy`). Copy the template:

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

A host may belong to several groups.

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

The server speaks MCP over **stdio**. Run it directly:

```bash
uv run lab-sentinel-mcp
```

Or register it in **Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "lab-sentinel": {
      "command": "uv",
      "args": ["run", "lab-sentinel-mcp"],
      "cwd": "/absolute/path/to/lab_mcp"
    }
  }
}
```

## Running the CLI Client

### Step 1 — Add the alias (one-time)

```bash
echo "alias sentinel='bash $(pwd)/sentinel.sh'" >> ~/.bashrc
source ~/.bashrc
```

### Step 2 — Start the chat

```bash
sentinel
```

You'll see a prompt:

```
╔══════════════════════════════════════════════════════╗
║           🛰️  MCP Lab Sentinel — Chat Mode           ║
║  Ask anything about your lab. Type 'exit' to quit.   ║
╚══════════════════════════════════════════════════════╝

🔍 You:
```

Type your question in natural language. The client launches the MCP server as a
subprocess, the model orchestrates the tools, and returns a Markdown answer.

> **One-shot mode** (for scripts): `sentinel "sua pergunta"` — answers and exits.

---

## Environment 1 — Real Hardware (Raspberry Pi)

If you already SSH into your boards, you're done. A typical `~/.ssh/config` with a jump
host:

```sshconfig
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
cp .sentinel.yaml.example .sentinel.yaml   # group your real hosts
uv run lab-sentinel-mcp                     # or use the CLI client
```

## Environment 2 — Virtual Machines

Works identically for VMs (VirtualBox, KVM, cloud). Just add SSH entries pointing at the
VM IP/port:

```sshconfig
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

Group them in `.sentinel.yaml` and run the server. No code changes — same path as real
hardware.

## Environment 3 — Docker Demo (no hardware needed)

Simulates a complete lab with 3 Alpine+SSH containers running locally.
All commands run from the **project root** (`lab_mcp/`).

### Step 1 — Generate the demo SSH key (one-time)

```bash
bash docker/setup-keys.sh
```

Output confirms the key was created at `docker/keys/sentinel_demo`.

### Step 2 — Start the containers

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Three containers start:

| Container | Port on localhost | Alias |
|-----------|-------------------|-------|
| sentinel-raspi01 | 2400 | `raspi01-demo` |
| sentinel-raspi02 | 2401 | `raspi02-demo` |
| sentinel-proxy109 | 2402 | `proxy109-demo` |

### Step 3 — Register the demo hosts in your SSH config (one-time)

```bash
cat docker/ssh_config.example >> ~/.ssh/config
```

Verify it works:

```bash
ssh raspi01-demo "echo connected"   # should print: connected
```

### Step 4 — Create the groups file

```bash
cp docker/.sentinel.yaml.example .sentinel.yaml
```

This creates a `laboratorio-demo` group pointing to the three containers.

### Step 5 — Start the sentinel chat

```bash
sentinel
```

### Suggested test questions (Docker)

Copy-paste these one by one at the `🔍 You:` prompt:

```
Quais máquinas estão registradas no grupo laboratorio-demo?
```
```
Todas as máquinas do laboratorio-demo estão online?
```
```
Qual sistema operacional cada máquina do laboratorio-demo usa?
```
```
Gere um relatório completo do laboratorio-demo.
```
```
Algum host do laboratorio-demo está com disco ou memória alta?
```
```
O meu arquivo ~/.ssh/config tem algum problema ou inconsistência?
```
```
Faça um checklist do laboratorio-demo como se fosse antes de uma aula.
```
```
raspi01-demo está com SSH funcionando? Qual é o uptime dele?
```

### Step 6 — Tear down when finished

```bash
docker compose -f docker/docker-compose.yml down
```

<details>
<summary>📄 Example output from a real run (see <code>examples/relatorio-exemplo.md</code>)</summary>

```markdown
# Lab Sentinel Report — laboratorio-demo

## Summary
- Hosts analyzed: 3
- Online: 3
- Offline: 0
- SSH working: 3
- Critical alerts: 0

## Hosts
### raspi01-demo
- Status: online
- SSH: working
- OS: Alpine Linux / Alpine Linux v3.20
- Disk: 6%
- Memory: 33%
- Uptime: 6:10
...
```

</details>

---

## Available Tools

| Tool | Input | Description |
|------|-------|-------------|
| `list_hosts` | `group?` | List registered hosts (sanitized — no key paths) |
| `ping_host` | `name` | Is the host reachable? Latency in ms |
| `check_ssh` | `name` | Does SSH connect? |
| `get_os_info` | `name` | OS, version, kernel, architecture |
| `get_resource_status` | `name` | Disk %, memory %, uptime, SSH service |
| `generate_report` | `filter_tag?` | Full Markdown report for a group |
| `check_ssh_config` | — | Audit `~/.ssh/config` for common issues |
| `suggest_fix` | `name` | Safe, read-only remediation tips |

## Resources & Prompts

**Resources** (readable context):
- `sentinel://hosts` — sanitized host inventory
- `sentinel://config` — SSH config audit summary

**Prompts** (ready-to-use templates):
- `analise_lab(group)` — full end-to-end lab analysis
- `status_geral()` — quick online/SSH status of all hosts
- `checklist_aula(group)` — pre-class readiness checklist

## Example Questions

**Inventário e conectividade**
```
Quais máquinas estão cadastradas?
Todas as máquinas do laboratorio-109 estão online?
raspi01-proxy está respondendo? Qual a latência?
```

**Sistema operacional e recursos**
```
Qual sistema operacional o raspi01-proxy usa?
Algum host está com disco acima de 80%?
Como está a memória de todas as máquinas?
Qual o uptime do proxy109?
```

**Relatórios**
```
Gere um relatório completo do laboratorio-109.
Faça um checklist do laboratorio-demo como se fosse antes de uma aula.
```

**Diagnóstico e sugestões**
```
O meu ~/.ssh/config tem inconsistências ou problemas?
O que devo fazer se o raspi02-proxy não responde?
Alguma máquina precisa de atenção agora?
```

## Test Cases

Run the suite with `uv run pytest` (64 tests). Key cases, in plain language:

| ID | Verifies | Expected result |
|----|----------|-----------------|
| **TC-001** | Unknown host is rejected | `ping_host("ghost")` → `HostNotFoundError` (`Host 'ghost' is not registered…`) |
| **TC-002** | Offline host detected | `ping_host` on a down host → `online: false` |
| **TC-003** | SSH config parsed | `proxy109` resolves to its real IP, port, ProxyJump |
| **TC-004** | Multi-alias blocks | `pc209` and `proxy209` both resolve from one block |
| **TC-005** | Groups from `.sentinel.yaml` | `list_hosts("laboratorio-109")` returns exactly the 3 members |
| **TC-006** | Auto-grouping convention | `raspi01-proxy` lands in auto-group `proxy` with no config file |
| **TC-007** | **Forbidden command blocked** | `rm -rf /`, `sudo reboot`, piped/chained commands → `SecurityError` |
| **TC-008** | OS parsing | Raspbian `/etc/os-release` + `uname` → correct OS/kernel/arch |
| **TC-009** | Resource parsing | `df`/`free`/`uptime` → disk %, memory %, uptime |
| **TC-010** | Offline host doesn't crash | `get_resource_status` on a dead host → empty status, no exception |
| **TC-011** | Report sections | Report always has Summary, Hosts, Alerts, Suggestions, timestamp |
| **TC-012** | High-disk alert | Disk ≥ 80% → alert + suggestion mentioning the host |
| **TC-013** | SSH config audit | Detects duplicate alias, missing IdentityFile, non-standard port |
| **TC-014** | **No key leakage** | `list_hosts` output never contains `identity_file` or key paths |
| **TC-015** | **Key only from `.env`** | A key in the shell env is ignored; missing `.env` key → `MissingKeyError` |

## Security Policy

This project is **secure by default** (see [ADR-004](docs/adr/ADR-004-security-boundaries.md)):

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
- [x] **Phase 2 — Advanced diagnostics**: resources, SSH-config audit, alerts
- [x] **Phase 3 — DevSecOps**: Docker, automated tests, full docs
- [ ] **Phase 4 — Extensions**: SQLite history, dashboard, run-to-run comparison, CI

---

<div align="center">
<sub>Built as a hands-on MCP lab for networking, IoT, OS, and DevSecOps courses.</sub>
</div>
