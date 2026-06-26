"""MCP server exposing Lab Sentinel as Tools, Resources, and Prompts.

This is a thin adapter over :class:`DiagnosticsService`. All sensitive data
(key paths, etc.) is stripped before it ever reaches the client.
"""

from __future__ import annotations

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from .diagnostics import DiagnosticsService
from .errors import SentinelError
from .factory import build_service
from .ssh_audit import audit_ssh_config


def build_server(service: DiagnosticsService) -> FastMCP:
    """Create and configure a FastMCP server bound to the given service."""
    mcp = FastMCP("lab-sentinel-mcp")

    # -- Tools -----------------------------------------------------------

    @mcp.tool()
    def list_hosts(group: str | None = None) -> dict:
        """List registered hosts from the SSH config inventory (sanitized)."""
        hosts = service.list_hosts(group=group)
        return {"hosts": [h.public_view() for h in hosts]}

    @mcp.tool()
    def ping_host(name: str) -> dict:
        """Check whether a registered host responds to ping."""
        try:
            result = service.ping_host(name)
        except SentinelError as exc:
            return {"name": name, "error": str(exc)}
        return {"name": name, "online": result.online, "latency_ms": result.latency_ms}

    @mcp.tool()
    def check_ssh(name: str) -> dict:
        """Verify that a registered host accepts an SSH connection."""
        try:
            result = service.check_ssh(name)
        except SentinelError as exc:
            return {"name": name, "error": str(exc)}
        return {"name": name, "ssh_ok": result.ssh_ok, "message": result.message}

    @mcp.tool()
    def get_os_info(name: str) -> dict:
        """Get OS, version, kernel and architecture of a host via SSH."""
        try:
            info = service.get_os_info(name)
        except SentinelError as exc:
            return {"name": name, "error": str(exc)}
        return {"name": name, **asdict(info)}

    @mcp.tool()
    def get_resource_status(name: str) -> dict:
        """Get disk, memory, uptime and SSH-service status of a host."""
        try:
            status = service.get_resource_status(name)
        except SentinelError as exc:
            return {"name": name, "error": str(exc)}
        return {"name": name, **asdict(status)}

    @mcp.tool()
    def generate_report(filter_tag: str | None = None) -> dict:
        """Generate a consolidated Markdown report for a group (or all hosts)."""
        return {"report_markdown": service.generate_report(group=filter_tag)}

    @mcp.tool()
    def check_ssh_config() -> dict:
        """Audit the local ~/.ssh/config for common issues (read-only)."""
        import os

        path = os.getenv("SENTINEL_SSH_CONFIG", "~/.ssh/config")
        return {"findings": audit_ssh_config(path)}

    @mcp.tool()
    def suggest_fix(name: str) -> dict:
        """Suggest safe, read-only remediation steps for a host."""
        from .report import suggest_fix as _suggest

        try:
            diag = service.diagnose_host(name)
        except SentinelError as exc:
            return {"name": name, "error": str(exc)}
        return {"name": name, "suggestions": _suggest(diag)}

    # -- Resources -------------------------------------------------------

    @mcp.resource("sentinel://hosts")
    def hosts_resource() -> dict:
        """Sanitized host inventory (no key paths)."""
        return {"hosts": [h.public_view() for h in service.list_hosts()]}

    @mcp.resource("sentinel://config")
    def config_resource() -> dict:
        """SSH config audit summary (no sensitive values)."""
        import os

        path = os.getenv("SENTINEL_SSH_CONFIG", "~/.ssh/config")
        return {"findings": audit_ssh_config(path)}

    # -- Prompts ---------------------------------------------------------

    @mcp.prompt()
    def analise_lab(group: str) -> str:
        """Analyze a lab group end-to-end and produce a full report."""
        return (
            f"Analyze the lab group '{group}'. Call list_hosts(group='{group}'), "
            "then ping_host, check_ssh, get_os_info and get_resource_status for each host, "
            "and finally generate_report(filter_tag) to summarize. "
            "Report which machines are online, their OS, and any problems needing attention."
        )

    @mcp.prompt()
    def status_geral() -> str:
        """Quick status check across all registered hosts."""
        return (
            "Give me a quick status of all hosts. Use list_hosts, then ping_host and "
            "check_ssh for each, and summarize online/offline and SSH state."
        )

    @mcp.prompt()
    def checklist_aula(group: str) -> str:
        """Pre-class checklist: connectivity, SSH, disk and memory."""
        return (
            f"Run a pre-class checklist for group '{group}': confirm every host is online, "
            "SSH works, disk usage is below 80% and memory below 85%. "
            "Flag anything that would disrupt a class and call generate_report."
        )

    return mcp


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    build_server(build_service()).run()


if __name__ == "__main__":
    main()
