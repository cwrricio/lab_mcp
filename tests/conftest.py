"""Shared fakes for the hexagonal ports, so the core is tested without I/O."""

import pytest

from lab_sentinel.domain.errors import HostNotFoundError, SecurityError
from lab_sentinel.domain.models import LabHost
from lab_sentinel.domain.results import PingResult


class FakeInventory:
    def __init__(self, hosts: list[LabHost]) -> None:
        self._hosts = {h.name: h for h in hosts}

    def list_hosts(self, group=None, name_filter=None):
        hosts = list(self._hosts.values())
        if group is not None:
            hosts = [h for h in hosts if group in h.tags]
        if name_filter is not None:
            needle = name_filter.lower()
            hosts = [h for h in hosts if needle in h.name.lower()]
        return hosts

    def get_host(self, name):
        try:
            return self._hosts[name]
        except KeyError:
            raise HostNotFoundError(name) from None


class FakePing:
    def __init__(self, online=True, latency_ms=12.0) -> None:
        self._result = PingResult(online=online, latency_ms=latency_ms)

    def ping(self, host):
        return self._result


class FakeSSH:
    """Configurable SSH double. ``outputs`` maps a command substring to stdout."""

    ALLOWED = {
        "cat /etc/os-release", "uname", "df -h /", "free -m", "uptime",
        "systemctl is-active ssh", "hostnamectl",
        "hostname -I", "ip addr show", "ip route show", "ip -6 addr show",
        "ss -tlnp", "cat /proc/net/arp", "iw dev",
    }

    def __init__(self, connect_ok=True, outputs=None) -> None:
        self._connect_ok = connect_ok
        self._outputs = outputs or {}

    def check_connection(self, host):
        if not self._connect_ok:
            return False
        return True

    def run_command(self, host, command):
        if not any(command.startswith(a) for a in self.ALLOWED):
            raise SecurityError()
        for key, value in self._outputs.items():
            if key in command:
                return value
        return ""


@pytest.fixture
def sample_hosts():
    return [
        LabHost(name="raspi01-proxy", host="localhost", user="pi", port=2400,
                tags=["proxy", "laboratorio-109"]),
        LabHost(name="raspi02-proxy", host="localhost", user="pi", port=2401,
                tags=["proxy", "laboratorio-109"]),
    ]
