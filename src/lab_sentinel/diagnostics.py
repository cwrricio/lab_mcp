"""Core diagnostics service — pure orchestration over the ports.

Contains no I/O itself: it depends only on InventoryPort, PingPort and
SSHClientPort, which makes every method unit-testable with fakes.
"""

from __future__ import annotations

from .ports import InventoryPort, PingPort, SSHClientPort
from .results import PingResult, SSHCheckResult


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
