"""Exception classes and the exit code each one maps to. Vendor-neutral."""


class BriefbenchError(Exception):
    """Base class. Messages are safe to print: anything from outside has been scrubbed."""

    exit_code = 1


class UsageError(BriefbenchError):
    """Fix the command: a bad flag value or an empty prompt."""

    exit_code = 2


class ConfigError(BriefbenchError):
    """Fix the setup: an unusable data folder, or an agent CLI that is missing or not logged in."""

    exit_code = 3
