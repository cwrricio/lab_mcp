"""Tests for report generation, SSH-config audit, and fix suggestions."""

import textwrap

from lab_sentinel.core.report import build_report, suggest_fix
from lab_sentinel.adapters.ssh_audit import audit_ssh_config
from lab_sentinel.domain.results import HostDiagnostic, OSInfo, ResourceStatus

DISK_ALERT = 90
MEM_OK = 40


def _diag(name, online=True, ssh_ok=True, disk=50, mem=MEM_OK):
    return HostDiagnostic(
        name=name,
        online=online,
        ssh_ok=ssh_ok,
        os=OSInfo(os="Raspbian", version="Debian 12 (bookworm)", kernel="6.6", architecture="aarch64"),
        resources=ResourceStatus(disk_used_percent=disk, memory_used_percent=mem,
                                 uptime="3 days", ssh_active=True),
    )


# -- build_report --------------------------------------------------------

def test_report_includes_all_sections():
    md = build_report([_diag("raspi01")], group="laboratorio-109")
    for section in ["# ", "## Summary", "## Hosts", "## Alerts", "## Suggestions"]:
        assert section in md


def test_report_includes_timestamp():
    md = build_report([_diag("raspi01")])
    assert "Generated at" in md


def test_report_marks_offline_host():
    md = build_report([_diag("raspi02", online=False, ssh_ok=False)])
    assert "offline" in md.lower()


def test_report_alerts_on_high_disk_usage():
    md = build_report([_diag("raspi01", disk=DISK_ALERT)])
    assert "disk" in md.lower()
    assert "raspi01" in md


def test_report_summary_counts():
    md = build_report([_diag("a"), _diag("b", online=False, ssh_ok=False)])
    assert "Online: 1" in md
    assert "Offline: 1" in md


# -- suggest_fix ---------------------------------------------------------

def test_suggest_fix_for_offline_host():
    tips = suggest_fix(_diag("x", online=False, ssh_ok=False))
    assert any("power" in t.lower() or "network" in t.lower() for t in tips)


def test_suggest_fix_for_high_disk():
    tips = suggest_fix(_diag("x", disk=95))
    assert any("disk" in t.lower() or "log" in t.lower() for t in tips)


def test_suggest_fix_healthy_host_has_no_alerts():
    assert suggest_fix(_diag("x", disk=10, mem=10)) == []


# -- audit_ssh_config ----------------------------------------------------

CONFIG_WITH_ISSUES = textwrap.dedent(
    """
    Host alpha
        HostName 10.0.0.1
        User pi

    Host alpha
        HostName 10.0.0.2

    Host beta
        HostName 10.0.0.3
        Port 2222
        IdentityFile ~/.ssh/id_beta
        ServerAliveInterval 60
    """
)


def test_audit_detects_duplicate_alias(tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text(CONFIG_WITH_ISSUES)
    findings = audit_ssh_config(cfg)
    assert any("duplicate" in f.lower() and "alpha" in f.lower() for f in findings)


def test_audit_detects_missing_identity_file(tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text(CONFIG_WITH_ISSUES)
    findings = audit_ssh_config(cfg)
    assert any("identityfile" in f.lower() and "alpha" in f.lower() for f in findings)


def test_audit_detects_non_standard_port(tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text(CONFIG_WITH_ISSUES)
    findings = audit_ssh_config(cfg)
    assert any("port" in f.lower() and "beta" in f.lower() for f in findings)


def test_audit_clean_config_has_no_findings(tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("Host ok\n    HostName 10.0.0.9\n    IdentityFile ~/.ssh/id_ok\n    ServerAliveInterval 60\n")
    assert audit_ssh_config(cfg) == []
