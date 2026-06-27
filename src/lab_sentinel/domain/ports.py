"""Ports (interfaces) for the hexagonal architecture.

The core domain depends on these Protocols, never on concrete adapters. This
keeps business logic testable with fakes and lets backends be swapped freely.
"""

from typing import Protocol

from lab_sentinel.domain.models import LabHost


class InventoryPort(Protocol):
    """Source of the host allowlist."""

    def list_hosts(self, group: str | None = None, name_filter: str | None = None) -> list[LabHost]: ...

    def get_host(self, name: str) -> LabHost:
        """Return the host or raise ``HostNotFoundError``."""
        ...


class PingResult(Protocol):
    online: bool
    latency_ms: float | None


class PingPort(Protocol):
    """Network reachability check."""

    def ping(self, host: LabHost) -> "PingResult": ...


class SSHClientPort(Protocol):
    """SSH connectivity and whitelisted remote command execution."""

    def check_connection(self, host: LabHost) -> bool: ...

    def run_command(self, host: LabHost, command: str) -> str:
        """Run a whitelisted command, returning stdout. Raise ``SecurityError``
        if the command is not allowed."""
        ...
