"""Exception classes and the exit code each one maps to. Vendor-neutral."""


class BriefbenchError(Exception):
    """Base class. Messages are safe to print: anything from outside has been redacted."""

    exit_code = 1


class UsageError(BriefbenchError):
    """Fix the command: bad flag value, empty prompt, a key value in the prompt."""

    exit_code = 2


class ConfigError(BriefbenchError):
    """Fix the setup: no provider, key unset or malformed, unusable data dir, bad playbook."""

    exit_code = 3


class ProviderError(BriefbenchError):
    """Anything between sending the request and holding a usable 2xx chat completion."""

    SETUP_KINDS = frozenset({"auth", "not_found", "bad_request", "quota", "redirect"})
    # every other kind is transient: rate_limit, server, timeout, network, tls, bad_response

    def __init__(self, kind, message, *, status=None, attempts=1, latency_ms=None):
        super().__init__(message)
        self.kind, self.status, self.attempts, self.latency_ms = kind, status, attempts, latency_ms

    @property
    def exit_code(self):
        return 3 if self.kind in self.SETUP_KINDS else 4


class OutputError(BriefbenchError):
    """A reply arrived but can't be used: empty, cut off, blocked, refused or unparseable."""

    exit_code = 5

    def __init__(self, kind, message, completion=None):
        super().__init__(message)
        self.kind, self.completion = kind, completion
