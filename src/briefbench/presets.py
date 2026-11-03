"""Vendor-specific settings: the only module that names vendors, their agent CLIs or their key variables.
Stage 2 adds how to run each agent CLI as worker, rewriter and judge (docs/design.md, "Runner")."""
from __future__ import annotations

from typing import Mapping

from .redact import MIN_SECRET

# briefbench never uses these. It removes them from every agent CLI's environment, so the CLI runs on your
# subscription login instead of billing an API account, and it scrubs their values from what it prints and logs.
KEY_ENVS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CODEX_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
            "OPENAI_API_KEY")


def secret_values(environ: Mapping[str, str]) -> list[str]:
    """The values of the key variables that are set. Shorter ones, such as placeholders, are ignored."""
    values = ((environ.get(name) or "").strip() for name in KEY_ENVS)
    return [v for v in values if len(v) >= MIN_SECRET]
