"""Markdown report generation and safe fix suggestions (pure functions)."""

from __future__ import annotations

from datetime import datetime, timezone

from lab_sentinel.domain.results import HostDiagnostic

DISK_ALERT_THRESHOLD = 80
MEMORY_ALERT_THRESHOLD = 85


def suggest_fix(diag: HostDiagnostic) -> list[str]:
    """Return safe, read-only remediation tips for a host. Never executes anything."""
    tips: list[str] = []
    if not diag.online:
        tips.append(
            f"{diag.name} is offline: check power, cabling, Wi-Fi, IP address or DNS."
        )
        return tips
    if not diag.ssh_ok:
        tips.append(
            f"{diag.name} answered ping but SSH failed: check user, key, port and firewall."
        )
    res = diag.resources
    if res and res.disk_used_percent is not None and res.disk_used_percent >= DISK_ALERT_THRESHOLD:
        tips.append(
            f"{diag.name} disk usage is {res.disk_used_percent}%: review old logs and temp files."
        )
    if res and res.memory_used_percent is not None and res.memory_used_percent >= MEMORY_ALERT_THRESHOLD:
        tips.append(
            f"{diag.name} memory usage is {res.memory_used_percent}%: review running processes."
        )
    return tips


def _alerts(diag: HostDiagnostic) -> list[str]:
    alerts: list[str] = []
    if not diag.online:
        alerts.append(f"{diag.name} did not respond to ping.")
        return alerts
    if not diag.ssh_ok:
        alerts.append(f"{diag.name} is online but SSH is not working.")
    res = diag.resources
    if res and res.disk_used_percent is not None and res.disk_used_percent >= DISK_ALERT_THRESHOLD:
        alerts.append(f"{diag.name} disk usage is above {DISK_ALERT_THRESHOLD}% ({res.disk_used_percent}%).")
    if res and res.memory_used_percent is not None and res.memory_used_percent >= MEMORY_ALERT_THRESHOLD:
        alerts.append(f"{diag.name} memory usage is above {MEMORY_ALERT_THRESHOLD}% ({res.memory_used_percent}%).")
    return alerts


def build_report(diagnostics: list[HostDiagnostic], group: str | None = None) -> str:
    """Render a consolidated Markdown report from per-host diagnostics."""
    title = f"# Lab Sentinel Report{f' — {group}' if group else ''}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    online = sum(1 for d in diagnostics if d.online)
    offline = len(diagnostics) - online
    ssh_ok = sum(1 for d in diagnostics if d.ssh_ok)

    all_alerts = [a for d in diagnostics for a in _alerts(d)]
    all_tips = [t for d in diagnostics for t in suggest_fix(d)]

    lines = [
        title,
        "",
        f"_Generated at {timestamp}._",
        "",
        "## Summary",
        f"- Hosts analyzed: {len(diagnostics)}",
        f"- Online: {online}",
        f"- Offline: {offline}",
        f"- SSH working: {ssh_ok}",
        f"- Critical alerts: {len(all_alerts)}",
        "",
        "## Hosts",
    ]

    for d in diagnostics:
        lines.append(f"### {d.name}")
        lines.append(f"- Status: {'online' if d.online else 'offline'}")
        if not d.online:
            lines.append("- SSH: not tested")
            lines.append("")
            continue
        lines.append(f"- SSH: {'working' if d.ssh_ok else 'failed'}")
        if d.os:
            lines.append(f"- OS: {d.os.os or 'unknown'} / {d.os.version or 'unknown'}")
            lines.append(f"- Kernel: {d.os.kernel or 'unknown'} ({d.os.architecture or 'unknown'})")
        if d.resources:
            r = d.resources
            lines.append(f"- Disk: {_fmt_pct(r.disk_used_percent)}")
            lines.append(f"- Memory: {_fmt_pct(r.memory_used_percent)}")
            lines.append(f"- Uptime: {r.uptime or 'unknown'}")
        if d.network:
            n = d.network
            if n.default_gateway:
                lines.append(f"- Gateway: {n.default_gateway}")
            active_ifaces = [i for i in n.interfaces if i.state == "UP" and i.ipv4]
            if active_ifaces:
                for iface in active_ifaces:
                    ips = ", ".join(iface.ipv4)
                    lines.append(f"- Interface {iface.name}: {ips}")
            if n.listening_services:
                lines.append(f"- Listening: {', '.join(n.listening_services)}")
            if n.arp_neighbors:
                lines.append(f"- ARP neighbors: {len(n.arp_neighbors)} host(s) on LAN")
        lines.append("")

    lines.append("## Alerts")
    lines.extend([f"- {a}" for a in all_alerts] or ["- No alerts."])
    lines.append("")
    lines.append("## Suggestions")
    lines.extend([f"- {t}" for t in all_tips] or ["- No action needed."])
    lines.append("")

    return "\n".join(lines)


def _fmt_pct(value: int | None) -> str:
    return f"{value}%" if value is not None else "unknown"
