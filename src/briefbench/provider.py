"""The one interface every model provider implements. Vendor-neutral."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user"]
    content: str


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None        # usage.prompt_tokens
    output_tokens: int | None = None       # usage.completion_tokens
    reasoning_tokens: int | None = None    # usage.completion_tokens_details.reasoning_tokens
    raw: Mapping[str, Any] | None = None   # the usage object exactly as returned


@dataclass(frozen=True)
class Completion:
    text: str                       # visible answer; reasoning fields and a leading <think> block are left out
    finish_reason: str | None       # lower-cased, as reported
    model_reported: str | None      # the response's "model" field: what actually answered
    response_id: str | None
    system_fingerprint: str | None
    refusal: str | None             # message.refusal, if the API set one
    reasoning_only: bool            # no visible text, but a reasoning field or <think> reasoning had content
    usage: Usage
    latency_ms: int                 # all attempts, including waits between them
    attempts: int


@dataclass(frozen=True)
class ProviderInfo:
    """Everything the log and the display need about the endpoint. Never holds a secret."""

    name: str                       # preset name, or "custom"
    vendor: str | None              # who makes the model; None for custom endpoints
    base_url: str                   # validated: no credentials, query or trailing slash
    model: str                      # model id requested
    key_env: str | None             # NAME of the variable holding the key; None = no key sent
    token_param: str                # "max_tokens" or "max_completion_tokens"
    params: Mapping[str, Any] = field(default_factory=dict)   # extra body fields for this model
    chosen_by: str = ""             # "--provider", "--base-url" or "auto: <key variable> is set"
    timeout_s: float = 120.0


class Provider(Protocol):
    info: ProviderInfo

    def complete(self, messages: Sequence[Message], *, max_output_tokens: int) -> Completion:
        """One chat completion, no tools. Raises briefbench.errors.ProviderError."""

    def preview(self, messages: Sequence[Message], *, max_output_tokens: int) -> dict[str, Any]:
        """{"url", "headers", "body"} that complete() would send, with no secret in it."""
