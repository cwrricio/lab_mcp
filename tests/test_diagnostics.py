"""Tests for the DiagnosticsService core (Issues #3 and #4)."""

import pytest

from lab_sentinel.diagnostics import DiagnosticsService
from lab_sentinel.errors import HostNotFoundError
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
