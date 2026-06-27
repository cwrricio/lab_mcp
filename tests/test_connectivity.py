"""Tests for the concrete connectivity adapters (Issues #3 and #4)."""

import subprocess

import pytest

from lab_sentinel.adapters.connectivity import (
    ALLOWED_COMMANDS,
    ParamikoSSHAdapter,
    SubprocessPingAdapter,
    _assert_allowed,
)
from lab_sentinel.domain.errors import SecurityError
from lab_sentinel.domain.models import LabHost

HOST = LabHost(name="h", host="localhost", user="pi", port=22)


def test_ping_online_parses_latency(mocker):
    mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="64 bytes time=12.3 ms", stderr=""
        ),
    )
    result = SubprocessPingAdapter().ping(HOST)
    assert result.online is True
    assert result.latency_ms == 12.3


def test_ping_offline_on_nonzero_exit(mocker):
    mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
    )
    assert SubprocessPingAdapter().ping(HOST).online is False


def test_ping_offline_on_timeout(mocker):
    mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ping", timeout=2))
    assert SubprocessPingAdapter().ping(HOST).online is False


@pytest.mark.parametrize("cmd", sorted(ALLOWED_COMMANDS))
def test_whitelisted_commands_pass(cmd):
    _assert_allowed(cmd)  # must not raise


@pytest.mark.parametrize(
    "cmd",
    [
        "rm -rf /",
        "sudo reboot",
        "cat /etc/os-release; rm file",
        "uname -a && shutdown now",
        "cat /etc/shadow",
        "df -h / | rm",
    ],
)
def test_forbidden_commands_raise_security_error(cmd):
    with pytest.raises(SecurityError):
        _assert_allowed(cmd)


def test_run_command_rejects_unlisted_before_connecting():
    # Should raise SecurityError without ever opening a connection.
    with pytest.raises(SecurityError):
        ParamikoSSHAdapter().run_command(HOST, "rm -rf /")
