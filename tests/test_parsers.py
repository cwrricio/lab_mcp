"""Unit tests for the pure output parsers."""

from lab_sentinel import parsers


def test_parse_os_release():
    name, version = parsers.parse_os_release(
        'NAME="Raspbian GNU/Linux"\nPRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\n'
    )
    assert name == "Raspbian GNU/Linux"
    assert "bookworm" in version


def test_parse_uname():
    kernel, arch = parsers.parse_uname("Linux pi 6.6.20+rpt-rpi-v8 #1 SMP aarch64 GNU/Linux")
    assert kernel.startswith("6.6")
    assert arch == "aarch64"


def test_parse_disk_percent():
    assert parsers.parse_disk_percent("/dev/root 15G 12G 2.5G 82% /") == 82


def test_parse_memory_percent():
    assert parsers.parse_memory_percent("Mem:  1000  610  200") == 61


def test_parse_uptime():
    assert "3 days" in parsers.parse_uptime(" 14:02 up 3 days,  4:11,  1 user, load 0.1")


def test_parse_disk_percent_missing_returns_none():
    assert parsers.parse_disk_percent("no percent here") is None
