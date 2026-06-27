"""Inventory adapter backed by the user's SSH config and an optional groups file.

This is the single source of the host allowlist. The AI model can only target
hosts that appear here; arbitrary IPs are never accepted.
"""

from __future__ import annotations

import os
from pathlib import Path

import paramiko
import yaml

from lab_sentinel.domain.errors import HostNotFoundError
from lab_sentinel.domain.models import LabHost

DEFAULT_SSH_CONFIG = "~/.ssh/config"
DEFAULT_GROUPS_FILE = ".sentinel.yaml"


def _expand(path: str | os.PathLike[str]) -> Path:
    return Path(os.path.expanduser(str(path)))


class SSHConfigInventoryAdapter:
    """Parses ``~/.ssh/config`` into :class:`LabHost` objects.

    Grouping precedence:
      1. Explicit groups from ``.sentinel.yaml`` (if present).
      2. Auto-grouping by the ``<device>-<env>`` alias convention as a fallback.
    """

    def __init__(
        self,
        ssh_config_path: str | os.PathLike[str] = DEFAULT_SSH_CONFIG,
        groups_file: str | os.PathLike[str] = DEFAULT_GROUPS_FILE,
    ) -> None:
        self._ssh_config_path = _expand(ssh_config_path)
        self._groups_file = _expand(groups_file)
        self._explicit_groups = self._load_groups()
        self._hosts = self._load_hosts()

    # -- loading ---------------------------------------------------------

    def _load_groups(self) -> dict[str, list[str]]:
        if not self._groups_file.is_file():
            return {}
        data = yaml.safe_load(self._groups_file.read_text()) or {}
        return data.get("groups", {}) or {}

    def _load_hosts(self) -> dict[str, LabHost]:
        hosts: dict[str, LabHost] = {}
        if not self._ssh_config_path.is_file():
            return hosts

        ssh_config = paramiko.SSHConfig()
        with self._ssh_config_path.open() as fh:
            ssh_config.parse(fh)

        for alias in self._iter_aliases():
            opts = ssh_config.lookup(alias)
            hostname = opts.get("hostname", alias)
            identity = opts.get("identityfile")
            if isinstance(identity, list):
                identity = identity[0] if identity else None
            hosts[alias] = LabHost(
                name=alias,
                host=hostname,
                user=opts.get("user", os.getenv("USER", "root")),
                port=int(opts.get("port", 22)),
                identity_file=identity,
                proxy_jump=opts.get("proxyjump"),
                tags=self._tags_for(alias),
            )
        return hosts

    def _iter_aliases(self) -> list[str]:
        """Concrete alias names from the SSH config, excluding wildcard patterns."""
        aliases: list[str] = []
        for line in self._ssh_config_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped.lower().startswith("host "):
                continue
            for token in stripped.split()[1:]:
                if "*" in token or "?" in token:
                    continue
                if token not in aliases:
                    aliases.append(token)
        return aliases

    def _tags_for(self, alias: str) -> list[str]:
        tags = [g for g, members in self._explicit_groups.items() if alias in members]
        auto = self._auto_group(alias)
        if auto and auto not in tags:
            tags.append(auto)
        return tags

    @staticmethod
    def _auto_group(alias: str) -> str | None:
        """`raspi01-proxy` -> `proxy`. Returns None when no `-` suffix exists."""
        if "-" in alias:
            return alias.rsplit("-", 1)[1]
        return None

    # -- InventoryPort ---------------------------------------------------

    def list_hosts(
        self,
        group: str | None = None,
        name_filter: str | None = None,
    ) -> list[LabHost]:
        hosts = list(self._hosts.values())
        if group is not None:
            hosts = [h for h in hosts if group in h.tags]
        if name_filter is not None:
            needle = name_filter.lower()
            hosts = [h for h in hosts if needle in h.name.lower()]
        return hosts

    def get_host(self, name: str) -> LabHost:
        try:
            return self._hosts[name]
        except KeyError:
            raise HostNotFoundError(name) from None
