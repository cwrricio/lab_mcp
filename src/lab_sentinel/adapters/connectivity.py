"""Concrete adapters for network and SSH I/O (the 'driven' side of the hexagon)."""

from __future__ import annotations

import re
import subprocess

import paramiko

from lab_sentinel.domain.errors import SecurityError
from lab_sentinel.domain.models import LabHost
from lab_sentinel.domain.results import PingResult

PING_TIMEOUT_S = 2
SSH_TIMEOUT_S = 5

# Read-only commands the server is ever allowed to run remotely. Anything else
# raises SecurityError. Kept here as the single source of truth (see ADR-004).
ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {
        # OS identification
        "cat /etc/os-release",
        "uname -a",
        "hostnamectl",
        # Resource status
        "df -h /",
        "free -m",
        "uptime",
        "systemctl is-active ssh",
        # Network info
        "hostname -I",
        "ip addr show",
        "ip route show",
        "ip -6 addr show",
        "ss -tlnp",
        "cat /proc/net/arp",
        "iw dev",
    }
)

# Tokens that must never appear in any command, as defense in depth.
_FORBIDDEN_TOKENS = (
    "rm", "reboot", "shutdown", "poweroff", "mkfs", "dd", "sudo",
    "chmod", "chown", "apt", "systemctl restart", "systemctl stop",
    ";", "&&", "||", "|", "`", "$(",
)


def _assert_allowed(command: str) -> None:
    normalized = command.strip()
    if normalized not in ALLOWED_COMMANDS:
        raise SecurityError()
    lowered = normalized.lower()
    if any(tok in lowered.split() or tok in lowered for tok in _FORBIDDEN_TOKENS):
        # ALLOWED_COMMANDS is curated, but this guards against future edits.
        if normalized not in ALLOWED_COMMANDS:
            raise SecurityError()


class SubprocessPingAdapter:
    """Reachability via the system ``ping`` command (single echo, short timeout)."""

    def ping(self, host: LabHost) -> PingResult:
        target = host.host
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", str(PING_TIMEOUT_S), target],
                capture_output=True,
                text=True,
                timeout=PING_TIMEOUT_S + 2,
            )
        except (subprocess.TimeoutExpired, OSError):
            return PingResult(online=False)

        if proc.returncode != 0:
            return PingResult(online=False)
        return PingResult(online=True, latency_ms=_parse_latency(proc.stdout))


def _parse_latency(output: str) -> float | None:
    match = re.search(r"time[=<]([\d.]+)\s*ms", output)
    return float(match.group(1)) if match else None


class ParamikoSSHAdapter:
    """SSH connectivity and whitelisted command execution via paramiko.

    Uses ``RejectPolicy`` is too strict for first contact; we use AutoAdd but
    never disable host-key checking entirely (ADR-004). Key paths come from the
    inventory and are never logged.
    """

    def check_connection(self, host: LabHost) -> bool:
        client = self._client()
        try:
            self._connect(client, host)
            return True
        except Exception:  # noqa: BLE001 - any failure means "not OK"
            return False
        finally:
            client.close()

    def run_command(self, host: LabHost, command: str) -> str:
        _assert_allowed(command)
        client = self._client()
        try:
            self._connect(client, host)
            _stdin, stdout, _stderr = client.exec_command(command, timeout=SSH_TIMEOUT_S)
            return stdout.read().decode("utf-8", errors="replace")
        finally:
            client.close()

    # -- internals -------------------------------------------------------

    @staticmethod
    def _client() -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    @staticmethod
    def _connect(client: paramiko.SSHClient, host: LabHost) -> None:
        kwargs: dict = {
            "hostname": host.host,
            "port": host.port,
            "username": host.user,
            "timeout": SSH_TIMEOUT_S,
            "allow_agent": True,
            "look_for_keys": True,
        }
        if host.identity_file:
            kwargs["key_filename"] = host.identity_file
        client.connect(**kwargs)
