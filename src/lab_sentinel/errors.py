"""Domain-specific exceptions with user-friendly messages."""


class SentinelError(Exception):
    """Base class for all Lab Sentinel errors."""


class HostNotFoundError(SentinelError):
    """Raised when a requested host is not in the inventory (the allowlist)."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Host '{name}' is not registered in the inventory.")
        self.name = name


class SecurityError(SentinelError):
    """Raised when an action violates the read-only security policy."""

    def __init__(self, message: str = "Command blocked by the Lab Sentinel security policy.") -> None:
        super().__init__(message)


class HostOfflineError(SentinelError):
    """Raised when a host is registered but does not respond."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Host '{name}' is registered but did not respond within the timeout."
        )
        self.name = name
