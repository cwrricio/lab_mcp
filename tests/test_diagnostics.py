"""Tests for the DiagnosticsService core (Issues #3 and #4)."""

import pytest

from lab_sentinel.core.diagnostics import DiagnosticsService
from lab_sentinel.domain.errors import HostNotFoundError
from tests.conftest import FakeInventory, FakePing, FakeSSH


def make_service(sample_hosts, *, online=True, connect_ok=True, outputs=None):
    return DiagnosticsService(
        inventory=FakeInventory(sample_hosts),
        ping=FakePing(online=online),
        ssh=FakeSSH(connect_ok=connect_ok, outputs=outputs),
    )


# -- ping_host -----------------------------------------------------------

def test_ping_online_host(sample_hosts):
    svc = make_service(sample_hosts, online=True)
    result = svc.ping_host("raspi01-proxy")
    assert result.online is True
    assert result.latency_ms is not None


def test_ping_offline_host(sample_hosts):
    svc = make_service(sample_hosts, online=False)
    assert svc.ping_host("raspi01-proxy").online is False


def test_ping_unknown_host_raises_error(sample_hosts):
    svc = make_service(sample_hosts)
    with pytest.raises(HostNotFoundError):
        svc.ping_host("ghost")


# -- check_ssh -----------------------------------------------------------

def test_check_ssh_success(sample_hosts):
    svc = make_service(sample_hosts, connect_ok=True)
    result = svc.check_ssh("raspi01-proxy")
    assert result.ssh_ok is True


def test_check_ssh_failure(sample_hosts):
    svc = make_service(sample_hosts, connect_ok=False)
    result = svc.check_ssh("raspi01-proxy")
    assert result.ssh_ok is False
    assert "fail" in result.message.lower() or "falh" in result.message.lower()


def test_check_ssh_unknown_host_raises_error(sample_hosts):
    svc = make_service(sample_hosts)
    with pytest.raises(HostNotFoundError):
        svc.check_ssh("ghost")


# -- get_os_info ---------------------------------------------------------

OS_RELEASE = (
    'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\n'
    'NAME="Raspbian GNU/Linux"\n'
    'VERSION_ID="12"\n'
)
UNAME = "Linux raspi 6.6.20+rpt-rpi-v8 #1 SMP aarch64 GNU/Linux"


def test_get_os_info_parses_output(sample_hosts):
    svc = make_service(
        sample_hosts,
        outputs={"cat /etc/os-release": OS_RELEASE, "uname": UNAME},
    )
    info = svc.get_os_info("raspi01-proxy")
    assert "Raspbian" in info.os
    assert "bookworm" in info.version
    assert info.kernel.startswith("6.6")
    assert info.architecture == "aarch64"


def test_get_os_info_falls_back_to_uname_when_no_os_release(sample_hosts):
    svc = make_service(sample_hosts, outputs={"cat /etc/os-release": "", "uname": UNAME})
    info = svc.get_os_info("raspi01-proxy")
    assert info.kernel.startswith("6.6")
    assert info.architecture == "aarch64"


# -- get_resource_status -------------------------------------------------

DF = "Filesystem Size Used Avail Use% Mounted on\n/dev/root 15G 12G 2.5G 82% /\n"
FREE = "              total        used        free\nMem:           1000         610         200\n"
UPTIME = " 14:02:01 up 3 days,  4:11,  1 user,  load average: 0.10"


def test_get_resource_status_parses_metrics(sample_hosts):
    svc = make_service(
        sample_hosts,
        outputs={
            "df -h /": DF,
            "free -m": FREE,
            "uptime": UPTIME,
            "systemctl is-active ssh": "active\n",
        },
    )
    status = svc.get_resource_status("raspi01-proxy")
    assert status.disk_used_percent == 82
    assert status.memory_used_percent == 61
    assert "3 days" in status.uptime
    assert status.ssh_active is True


def test_get_resource_status_handles_offline_host(sample_hosts):
    # SSH double that raises on connect -> service must not crash.
    from tests.conftest import FakeInventory, FakePing

    class DeadSSH:
        def check_connection(self, host):
            return False

        def run_command(self, host, command):
            raise OSError("host unreachable")

    svc = DiagnosticsService(
        inventory=FakeInventory(sample_hosts), ping=FakePing(online=False), ssh=DeadSSH()
    )
    status = svc.get_resource_status("raspi01-proxy")
    assert status.disk_used_percent is None
    assert status.ssh_active is False
