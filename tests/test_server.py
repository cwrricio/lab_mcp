"""Tests for the MCP server wiring and output sanitization (Issue #6)."""

import asyncio

from lab_sentinel.diagnostics import DiagnosticsService
from lab_sentinel.models import LabHost
from lab_sentinel.server import build_server
from tests.conftest import FakeInventory, FakePing, FakeSSH


def _server():
    hosts = [
        LabHost(name="raspi01-proxy", host="localhost", user="pi", port=2400,
                identity_file="~/.ssh/id_secret", tags=["proxy"]),
    ]
    service = DiagnosticsService(
        inventory=FakeInventory(hosts), ping=FakePing(), ssh=FakeSSH()
    )
    return build_server(service)


def test_all_tools_registered():
    server = _server()
    names = {t.name for t in asyncio.run(server.list_tools())}
    expected = {
        "list_hosts", "ping_host", "check_ssh", "get_os_info",
        "get_resource_status", "generate_report", "check_ssh_config", "suggest_fix",
    }
    assert expected <= names


def test_resources_registered():
    server = _server()
    uris = {str(r.uri) for r in asyncio.run(server.list_resources())}
    assert "sentinel://hosts" in uris
    assert "sentinel://config" in uris


def test_prompts_registered():
    server = _server()
    names = {p.name for p in asyncio.run(server.list_prompts())}
    assert {"analise_lab", "status_geral", "checklist_aula"} <= names


def test_list_hosts_tool_excludes_identity_file():
    server = _server()
    result = asyncio.run(server.call_tool("list_hosts", {}))
    text = str(result)
    assert "id_secret" not in text
    assert "identity_file" not in text
