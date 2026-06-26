"""Core domain models shared across the application."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LabHost:
    """A host the sentinel is allowed to diagnose.

    Built from a single `Host` entry in the user's SSH config. ``identity_file``
    is kept for connectivity but must never be exposed in tool/resource output
    (see ``public_view``).
    """

    name: str
    host: str
    user: str
    port: int = 22
    identity_file: str | None = None
    proxy_jump: str | None = None
    tags: list[str] = field(default_factory=list)

    def public_view(self) -> dict:
        """Return a sanitized representation safe to expose to AI clients.

        Deliberately omits ``identity_file`` so private-key paths never leak.
        """
        return {
            "name": self.name,
            "host": self.host,
            "user": self.user,
            "port": self.port,
            "proxy_jump": self.proxy_jump,
            "tags": list(self.tags),
        }
