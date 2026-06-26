"""Pure parsers turning raw command output into structured results.

Separated from I/O so they are trivially unit-testable and reusable.
"""

from __future__ import annotations

import re

from .results import OSInfo, ResourceStatus


def parse_os_release(text: str) -> tuple[str | None, str | None]:
    """Return ``(name, version)`` from /etc/os-release content."""
    fields = {}
    for line in text.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            fields[key.strip()] = value.strip().strip('"')
    name = fields.get("NAME")
    version = fields.get("PRETTY_NAME") or fields.get("VERSION")
    return name, version


def parse_uname(text: str) -> tuple[str | None, str | None]:
    """Return ``(kernel, architecture)`` from ``uname -a`` output."""
    tokens = text.split()
    kernel = tokens[2] if len(tokens) > 2 else None
    arch = next((t for t in tokens if t in {"aarch64", "x86_64", "armv7l", "arm64", "i686"}), None)
    return kernel, arch


def build_os_info(os_release: str, uname: str) -> OSInfo:
    name, version = parse_os_release(os_release)
    kernel, arch = parse_uname(uname)
    return OSInfo(os=name, version=version, kernel=kernel, architecture=arch)


def parse_disk_percent(df_output: str) -> int | None:
    match = re.search(r"(\d+)%", df_output)
    return int(match.group(1)) if match else None


def parse_memory_percent(free_output: str) -> int | None:
    for line in free_output.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            if len(parts) >= 3:
                total, used = float(parts[1]), float(parts[2])
                if total > 0:
                    return round(used / total * 100)
    return None


def parse_uptime(uptime_output: str) -> str | None:
    match = re.search(r"up\s+(.+?),\s+\d+\s+user", uptime_output)
    return match.group(1).strip() if match else (uptime_output.strip() or None)


def build_resource_status(
    df: str, free: str, uptime: str, ssh_active: str
) -> ResourceStatus:
    return ResourceStatus(
        disk_used_percent=parse_disk_percent(df),
        memory_used_percent=parse_memory_percent(free),
        uptime=parse_uptime(uptime),
        ssh_active="active" in ssh_active.strip().lower(),
    )
