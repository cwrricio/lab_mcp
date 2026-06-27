"""Plain result objects returned by diagnostics (transport-agnostic)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PingResult:
    online: bool
    latency_ms: float | None = None


@dataclass(frozen=True)
class SSHCheckResult:
    ssh_ok: bool
    message: str


@dataclass(frozen=True)
class OSInfo:
    os: str | None = None
    version: str | None = None
    kernel: str | None = None
    architecture: str | None = None


@dataclass(frozen=True)
class ResourceStatus:
    disk_used_percent: int | None = None
    memory_used_percent: int | None = None
    uptime: str | None = None
    ssh_active: bool | None = None


@dataclass(frozen=True)
class NetworkInterface:
    name: str
    ipv4: list[str] = field(default_factory=list)
    ipv6: list[str] = field(default_factory=list)
    mac: str | None = None
    state: str | None = None


@dataclass(frozen=True)
class NetworkInfo:
    hostname: str | None = None
    interfaces: list[NetworkInterface] = field(default_factory=list)
    default_gateway: str | None = None
    routes: list[str] = field(default_factory=list)
    listening_services: list[str] = field(default_factory=list)
    arp_neighbors: list[str] = field(default_factory=list)


@dataclass
class HostDiagnostic:
    """Full diagnostic snapshot for one host, used to build reports."""

    name: str
    online: bool = False
    ssh_ok: bool = False
    os: OSInfo | None = None
    resources: ResourceStatus | None = None
    network: NetworkInfo | None = None
