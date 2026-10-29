"""Vendor-specific settings: the only module that names vendors, hosts, key variables or model ids.

Endpoints and auth error shapes were checked on 2026-10-28 with a fake key. Request parameters come
from each vendor's documentation. No preset has completed a real rewrite yet; `uv run pytest -m live`
with keys set is that check.

Error bodies the client parses, by vendor (verified with a fake key unless marked):
  OpenAI, Anthropic, Groq, OpenRouter: {"error": {"message": ...}}; OpenAI's 401 echoes 8+4 key characters.
  Gemini: a JSON array [{"error": {...}}]; a bad key is HTTP 400, not 401.
  Mistral: {"detail": ...}.  xAI (secondary source): {"code": ..., "error": "..."}, bad key may be HTTP 400.
  Cloudflare fronts: plain text such as "error code: 1010".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Preset:
    name: str
    vendor: str
    base_url: str
    key_env: str
    default_model: str
    token_param: str = "max_tokens"
    model_params: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)  # model id -> extra fields
    auth_hint: str = ""


PRESETS: dict[str, Preset] = {p.name: p for p in (
    Preset("anthropic", "anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "claude-haiku-5-5",
           auth_hint="If the key is not scoped to a workspace, Anthropic also needs an "
                     "anthropic-workspace-id header, which briefbench does not send."),
    Preset("gemini", "google", "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY",
           "gemini-3.5-flash-lite"),
    Preset("openai", "openai", "https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-6-luna",
           token_param="max_completion_tokens",
           model_params={"gpt-6-luna": {"reasoning_effort": "low"}}),
)}
