"""Core diagnostics service — pure orchestration over the ports.

Contains no I/O itself: it depends only on InventoryPort, PingPort and
SSHClientPort, which makes every method unit-testable with fakes.
"""

from __future__ import annotations

from . import parsers
from .ports import InventoryPort, PingPort, SSHClientPort
from .results import OSInfo, PingResult, ResourceStatus, SSHCheckResult


class DiagnosticsService:
    def __init__(
        self,
        inventory: InventoryPort,
        ping: PingPort,
        ssh: SSHClientPort,
    ) -> None:
        self._inventory = inventory
        self._ping = ping
        self._ssh = ssh

    def ping_host(self, name: str) -> PingResult:
        host = self._inventory.get_host(name)  # raises HostNotFoundError
        return self._ping.ping(host)

    def check_ssh(self, name: str) -> SSHCheckResult:
        host = self._inventory.get_host(name)
        try:
            ok = self._ssh.check_connection(host)
        except Exception as exc:  # noqa: BLE001 - report any failure safely
            return SSHCheckResult(ssh_ok=False, message=f"SSH connection failed: {exc}")
        if ok:
            return SSHCheckResult(ssh_ok=True, message="SSH connection established successfully.")
        return SSHCheckResult(ssh_ok=False, message="Host reachable, but SSH connection failed.")

    def get_os_info(self, name: str) -> OSInfo:
        host = self._inventory.get_host(name)
        os_release = self._safe_run(host, "cat /etc/os-release")
        uname = self._safe_run(host, "uname -a")
        return parsers.build_os_info(os_release, uname)

    def get_resource_status(self, name: str) -> ResourceStatus:
        host = self._inventory.get_host(name)
        df = self._safe_run(host, "df -h /")
        free = self._safe_run(host, "free -m")
        uptime = self._safe_run(host, "uptime")
        ssh_active = self._safe_run(host, "systemctl is-active ssh")
        if not any([df, free, uptime]):
            # Host unreachable: return an empty status rather than raising.
            return ResourceStatus(ssh_active=False)
        return parsers.build_resource_status(df, free, uptime, ssh_active)

    def _safe_run(self, host, command: str) -> str:
        """Run a command, returning empty string on any connectivity failure."""
        try:
            return self._ssh.run_command(host, command)
        except Exception:  # noqa: BLE001 - offline/unreachable handled gracefully
            return ""
