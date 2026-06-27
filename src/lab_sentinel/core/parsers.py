"""Pure parsers turning raw command output into structured results.

Separated from I/O so they are trivially unit-testable and reusable.
"""

from __future__ import annotations

import re

from lab_sentinel.domain.results import NetworkInfo, NetworkInterface, OSInfo, ResourceStatus


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


def parse_ip_addr(output: str) -> list[NetworkInterface]:
    """Parse ``ip addr show`` into a list of NetworkInterface objects."""
    interfaces: list[NetworkInterface] = []
    current_name: str | None = None
    current_mac: str | None = None
    current_state: str | None = None
    ipv4: list[str] = []
    ipv6: list[str] = []

    def _flush() -> None:
        if current_name:
            interfaces.append(NetworkInterface(
                name=current_name,
                ipv4=list(ipv4),
                ipv6=list(ipv6),
                mac=current_mac,
                state=current_state,
            ))

    for line in output.splitlines():
        m = re.match(r"^\d+:\s+(\S+?)[@:]?\s+<([^>]*)>", line)
        if m:
            _flush()
            current_name = m.group(1).rstrip(":")
            current_mac = None
            current_state = "UP" if "UP" in m.group(2) else "DOWN"
            ipv4 = []
            ipv6 = []
            continue
        m = re.search(r"link/ether\s+([0-9a-f:]{17})", line)
        if m:
            current_mac = m.group(1)
            continue
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+/\d+)", line)
        if m:
            ipv4.append(m.group(1))
            continue
        # Only global IPv6 — skip link-local (fe80::) to reduce noise
        m = re.search(r"inet6\s+([0-9a-f:]+/\d+)\s+scope\s+global", line)
        if m:
            ipv6.append(m.group(1))

    _flush()
    return interfaces


def parse_ip_route(output: str) -> tuple[str | None, list[str]]:
    """Return ``(default_gateway, routes)`` from ``ip route show``."""
    gateway: str | None = None
    routes: list[str] = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"default via (\S+)", line)
        if m:
            gateway = m.group(1)
        routes.append(line)
    return gateway, routes


def parse_ss(output: str) -> list[str]:
    """Parse ``ss -tlnp`` into human-readable service:port strings."""
    services: list[str] = []
    for line in output.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 4 or parts[0] != "LISTEN":
            continue
        local = parts[3]
        port = local.rsplit(":", 1)[-1]
        proc_match = re.search(r'"([^"]+)"', parts[-1]) if len(parts) > 5 else None
        name = proc_match.group(1) if proc_match else "unknown"
        entry = f"{name} :{port}"
        if entry not in services:
            services.append(entry)
    return services


def parse_arp(output: str) -> list[str]:
    """Parse ``/proc/net/arp`` into neighbor strings, skipping incomplete entries."""
    neighbors: list[str] = []
    for line in output.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 6:
            continue
        ip, flags, mac, iface = parts[0], parts[2], parts[3], parts[5]
        if flags == "0x0" or mac == "00:00:00:00:00:00":
            continue
        neighbors.append(f"{ip} via {iface} ({mac})")
    return neighbors


def parse_iw_dev(output: str) -> str | None:
    """Return a short WiFi summary string if a wireless interface is present."""
    ssid = re.search(r"ssid (.+)", output)
    channel = re.search(r"channel (\d+)", output)
    if ssid:
        parts = [f"SSID: {ssid.group(1).strip()}"]
        if channel:
            parts.append(f"channel {channel.group(1)}")
        return ", ".join(parts)
    return None


def build_network_info(
    hostname_i: str,
    ip_addr: str,
    ip_route: str,
    ss_output: str,
    arp_output: str,
    iw_output: str,
) -> NetworkInfo:
    hostname = hostname_i.strip().split()[0] if hostname_i.strip() else None
    interfaces = parse_ip_addr(ip_addr)
    gateway, routes = parse_ip_route(ip_route)
    services = parse_ss(ss_output)
    neighbors = parse_arp(arp_output)

    wifi_note = parse_iw_dev(iw_output)
    extra = ([f"wifi: {wifi_note}"] if wifi_note else [])

    return NetworkInfo(
        hostname=hostname,
        interfaces=interfaces,
        default_gateway=gateway,
        routes=routes,
        listening_services=extra + services,
        arp_neighbors=neighbors,
    )
