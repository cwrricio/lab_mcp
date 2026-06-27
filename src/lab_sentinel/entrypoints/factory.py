"""Composition root: assembles the DiagnosticsService from configuration.

Keeping wiring here (instead of in server/cli) lets both entry points and tests
construct a fully-wired service the same way.
"""

from __future__ import annotations

import os

from lab_sentinel.adapters.config import DEFAULT_GROUPS_FILE, DEFAULT_SSH_CONFIG, SSHConfigInventoryAdapter
from lab_sentinel.adapters.connectivity import ParamikoSSHAdapter, SubprocessPingAdapter
from lab_sentinel.core.diagnostics import DiagnosticsService


def build_service() -> DiagnosticsService:
    ssh_config = os.getenv("SENTINEL_SSH_CONFIG", DEFAULT_SSH_CONFIG)
    groups_file = os.getenv("SENTINEL_GROUPS_FILE", DEFAULT_GROUPS_FILE)
    inventory = SSHConfigInventoryAdapter(ssh_config, groups_file=groups_file)
    return DiagnosticsService(
        inventory=inventory,
        ping=SubprocessPingAdapter(),
        ssh=ParamikoSSHAdapter(),
    )
