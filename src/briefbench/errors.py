"""Exception classes and the exit code each one maps to. Vendor-neutral."""


class BriefbenchError(Exception):
    """Base class. Messages are safe to print: anything from outside has been scrubbed."""

    exit_code = 1


class UsageError(BriefbenchError):
    """Fix the command: a bad flag value, an unknown treatment or an empty prompt."""

    exit_code = 2


class ConfigError(BriefbenchError):
    """Fix the setup: an unusable data folder, an agent CLI that is missing or not on a plan login, or a
    treatment that changed since `init`."""

    exit_code = 3


class AgentError(BriefbenchError):
    """A trial step failed, such as setup or the headless rewrite; its log says why. Try again."""

    exit_code = 4
