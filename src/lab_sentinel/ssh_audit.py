"""Read-only audit of the user's SSH config (never modifies the file)."""

from __future__ import annotations

import os
from pathlib import Path

STANDARD_SSH_PORT = 22


def audit_ssh_config(path: str | os.PathLike[str]) -> list[str]:
    """Return a list of human-readable findings about common misconfigurations."""
    config_path = Path(os.path.expanduser(str(path)))
    if not config_path.is_file():
        return [f"SSH config not found at {config_path}."]

    blocks = _parse_blocks(config_path.read_text())
    findings: list[str] = []
    seen: set[str] = set()

    for alias, opts in blocks:
        if "*" in alias or "?" in alias:
            continue
        if alias in seen:
            findings.append(f"Duplicate alias '{alias}' declared more than once.")
        seen.add(alias)

        if "identityfile" not in opts:
            findings.append(f"Host '{alias}' has no IdentityFile configured.")
        if "serveraliveinterval" not in opts:
            findings.append(f"Host '{alias}' has no ServerAliveInterval set.")
        port = opts.get("port")
        if port and port.isdigit() and int(port) != STANDARD_SSH_PORT:
            findings.append(f"Host '{alias}' uses a non-standard port ({port}).")

    return findings


def _parse_blocks(text: str) -> list[tuple[str, dict[str, str]]]:
    """Parse into ``[(alias, {key: value})]`` preserving duplicate Host blocks."""
    blocks: list[tuple[str, dict[str, str]]] = []
    current: dict[str, str] | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(" ")
        key = key.strip().lower()
        value = value.strip()
        if key == "host":
            current = {}  # aliases on the same line share one options dict
            for alias in value.split():
                blocks.append((alias, current))
        elif current is not None:
            current[key] = value
    return blocks
