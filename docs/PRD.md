# Product Requirements Document — MCP Lab Sentinel

**Version:** 1.0  
**Date:** 2026-06-26  
**Status:** Approved

---

## 1. Problem Statement

In academic labs, IoT environments, and research rooms with multiple Raspberry Pi devices and Linux PCs, engineers lose significant time manually verifying:

- Which devices are powered on and reachable on the network
- Which SSH alias or IP to use for each machine
- What operating system and kernel version is installed
- Whether SSH access is functional
- Whether disk or memory is critically low
- Whether the lab is ready for a class, experiment, or demonstration

This process is repetitive, error-prone, and does not scale beyond a few machines.

---

## 2. Proposed Solution

**MCP Lab Sentinel** is a local MCP (Model Context Protocol) server that exposes structured diagnostic tools, resources, and prompts to AI clients. It allows a language model to answer natural-language questions about lab infrastructure by calling real, safe, read-only tools.

The server is environment-agnostic: it works with physical Raspberry Pi boards, Linux VMs, and Docker containers — relying solely on the user's existing `~/.ssh/config` for connectivity.

---

## 3. Goals

1. Expose a standards-compliant MCP server with Tools, Resources, and Prompts
2. Read host inventory from `~/.ssh/config` (zero extra config by default)
3. Support optional grouping via `.sentinel.yaml`
4. Provide a CLI client using OpenAI GPT-4o for natural language interaction
5. Work across three environments: real hardware, VMs, Docker
6. Never leak SSH keys, API keys, or sensitive paths in tool outputs
7. Execute only whitelisted, read-only commands on remote hosts

---

## 4. Non-Goals

- Executing destructive commands on remote hosts
- Accepting arbitrary IP addresses or commands from the AI model
- Modifying `~/.ssh/config` automatically
- Performing unauthorized network scans
- Replacing full monitoring solutions (Prometheus, Grafana, etc.)

---

## 5. Target Users

- Students and professors in networking, IoT, and OS courses
- Lab administrators managing Raspberry Pi fleets
- DevSecOps practitioners demonstrating infrastructure-as-code concepts
- Developers learning the MCP protocol with a real-world use case

---

## 6. Functional Requirements

### 6.1 MCP Tools (mandatory)

| Tool | Description |
|------|-------------|
| `list_hosts` | Lists all hosts from `~/.ssh/config`, filtered optionally by group |
| `ping_host` | Checks if a registered host responds to ping |
| `check_ssh` | Verifies SSH connectivity to a registered host |
| `get_os_info` | Retrieves OS, kernel, and architecture info via SSH |
| `get_resource_status` | Collects disk, memory, uptime, and SSH service status |
| `generate_report` | Produces a consolidated Markdown report for a group or all hosts |
| `check_ssh_config` | Analyzes local `~/.ssh/config` for common issues |
| `suggest_fix` | Generates safe remediation suggestions based on diagnostics |

### 6.2 MCP Resources

| Resource URI | Description |
|-------------|-------------|
| `sentinel://hosts` | Sanitized host inventory (no key paths) |
| `sentinel://config` | SSH config summary (no sensitive values) |

### 6.3 MCP Prompts

| Prompt | Description |
|--------|-------------|
| `analise-lab` | Analyzes a lab group and generates a full report |
| `status-geral` | Quick status check for all registered hosts |
| `checklist-aula` | Pre-class checklist: connectivity, SSH, disk, memory |

### 6.4 CLI Client

- Command: `uv run lab-sentinel "<natural language query>"`
- Uses OpenAI GPT-4o with tool calling
- Reads `OPENAI_API_KEY` exclusively from `.env` file
- Prints structured Markdown output to terminal

---

## 7. Non-Functional Requirements

### 7.1 Security
- Tool outputs must never include `IdentityFile` paths, private key content, or `.env` values
- Only hosts present in `~/.ssh/config` may be targeted
- All SSH commands must pass through a whitelist
- No `StrictHostKeyChecking=no` by default
- SSH connections use key-based auth only (no passwords stored)

### 7.2 Portability
- Works on Linux and macOS
- Three supported environments: physical hardware, VMs, Docker containers
- Docker demo requires only `docker compose up` to be fully operational

### 7.3 Developer Experience
- Managed with `uv` (no manual virtualenv)
- Full test suite runnable with `uv run pytest`
- TDD approach: tests written before implementation
- All code in English; comments only where the WHY is non-obvious

### 7.4 Code Quality
- SOLID principles throughout
- Clean Code conventions (meaningful names, small functions, no magic values)
- Hexagonal architecture: core logic independent of MCP transport and SSH backend

---

## 8. Inventory Configuration

### Default (zero config)
The server reads all `Host` entries from `~/.ssh/config`. Hosts named `<device>-<env>` are auto-grouped by the `<env>` suffix.

### Optional grouping (`.sentinel.yaml`)
```yaml
groups:
  laboratorio-109:
    - raspi01-proxy
    - raspi02-proxy
    - proxy109
  laboratorio-209:
    - raspi01-proxy209
    - raspi02-proxy209
    - proxy209
```

Users can create custom groups and assign any SSH alias to multiple groups.

---

## 9. Environments

### Real Hardware
- Raspberry Pi boards accessible via SSH (direct or via ProxyJump)
- Existing `~/.ssh/config` used as-is

### Virtual Machines
- VMs with SSH enabled
- SSH config entries added manually pointing to VM IPs/ports

### Docker (Demo)
- `docker compose up` starts 3 Alpine containers with SSH
- Containers expose ports `2400`, `2401`, `2402` on localhost
- Example SSH config and `.sentinel.yaml` provided

---

## 10. Acceptance Criteria (MVP)

- [ ] `~/.ssh/config` parsed correctly into host inventory
- [ ] `list_hosts` returns registered hosts without sensitive data
- [ ] `ping_host` identifies online/offline status
- [ ] `check_ssh` tests SSH connectivity
- [ ] `get_os_info` returns real OS data from remote host
- [ ] `get_resource_status` returns disk, memory, uptime
- [ ] `generate_report` produces readable Markdown
- [ ] `check_ssh_config` identifies common misconfigurations
- [ ] At least 10 automated tests passing
- [ ] CLI client works end-to-end with OpenAI GPT-4o
- [ ] Docker demo works with `docker compose up`
- [ ] README covers all three environments
- [ ] No tool leaks sensitive data

---

## 11. Out of Scope (Future Phases)

- SQLite history of diagnostic runs
- Dashboard UI
- GitHub Actions CI/CD
- Export report to `.md` file automatically
- Comparison between current and previous lab state
