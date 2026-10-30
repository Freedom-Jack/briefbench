"""Choose the endpoint, model and key from flags and the environment. Vendor-neutral: vendor
details arrive only as data from presets.PRESETS."""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Mapping

from .errors import ConfigError, UsageError
from .openai_compat import OpenAICompatProvider, is_loopback
from .presets import PRESETS
from .provider import ProviderInfo
from .redact import MIN_SECRET

ENV_NAME = re.compile(r"[A-Z_][A-Z0-9_]{0,127}")
KEY_CHARS = re.compile(r"[\x21-\x7e]+")        # printable ASCII without spaces


@dataclass(frozen=True)
class Selection:
    info: ProviderInfo
    api_key: str | None = field(repr=False)     # never in repr, output or the log
    auth_hint: str = ""
    others: tuple[str, ...] = ()                # other preset key variables that are set (auto-detect only)


def key_env_names(api_key_env: str | None = None) -> list[str]:
    names = {p.key_env for p in PRESETS.values()}
    if api_key_env:
        names.add(api_key_env)
    return sorted(names)


def secret_values(environ: Mapping[str, str], api_key_env: str | None = None) -> list[str]:
    """Values of every known key variable, for refusing and redacting them. Short values are ignored."""
    values = ((environ.get(n) or "").strip() for n in key_env_names(api_key_env))
    return [v for v in values if len(v) >= MIN_SECRET]


def detected(environ: Mapping[str, str]) -> list[str]:
    return [n for n in sorted(PRESETS) if (environ.get(PRESETS[n].key_env) or "").strip()]


def no_provider_message(dry_run: bool = False) -> str:
    names = [PRESETS[n].key_env for n in sorted(PRESETS)]
    listed = ", ".join(names[:-1]) + " or " + names[-1]
    return (f"no model provider is configured. Set one of {listed}, or use --base-url and --model "
            "for another OpenAI-compatible endpoint" +
            (", or pass --provider NAME to see the request without a key." if dry_run else "."))


def select_provider(*, provider, model, base_url, api_key_env, timeout_s, environ, require_key=True) -> Selection:
    if api_key_env is not None and not ENV_NAME.fullmatch(api_key_env):
        raise UsageError("--api-key-env takes the name of an environment variable (capital letters, digits "
                         "and _), not a key. The value you gave is not shown.")
    others: tuple[str, ...] = ()
    if provider:
        preset, chosen_by = PRESETS[provider], "--provider"          # argparse restricts the choices
    elif base_url:
        preset, chosen_by = None, "--base-url"
    elif api_key_env:
        raise UsageError("--api-key-env needs --provider or --base-url.")
    else:
        found = detected(environ)
        if not found:
            raise ConfigError(no_provider_message(dry_run=not require_key))
        preset = PRESETS[found[0]]
        chosen_by = f"auto: {preset.key_env} is set"
        others = tuple(PRESETS[n].key_env for n in found[1:])
    model_id = (model or "").strip() or (preset.default_model if preset else "")
    if not model_id:
        raise UsageError("--base-url needs --model.")
    key_env = api_key_env or (preset.key_env if preset else None)
    api_key = None
    if key_env:
        api_key = (environ.get(key_env) or "").strip() or None
        if api_key is None and require_key:
            raise ConfigError(f"{key_env} is not set. Export it in your shell, or choose another provider "
                              "with --provider.")
        if api_key is not None and not KEY_CHARS.fullmatch(api_key):
            raise ConfigError(f"{key_env} contains spaces, line breaks or other characters an API key can't "
                              "contain, so it was not used. Its value is not shown.")
    url = check_base_url(base_url or preset.base_url, sends_key=key_env is not None)   # as the real run would
    info = ProviderInfo(
        name=preset.name if preset else "custom",
        vendor=preset.vendor if preset else None,
        base_url=url,
        model=model_id,
        key_env=key_env,
        token_param=preset.token_param if preset else "max_tokens",
        params=dict(preset.model_params.get(model_id, {})) if preset else {},
        chosen_by=chosen_by,
        timeout_s=timeout_s,
    )
    return Selection(info, api_key, preset.auth_hint if preset else "", others)


def check_base_url(url: str, *, sends_key: bool) -> str:
    """Validate before anything is sent. Errors never echo the URL, which may hold a secret."""
    url = url.strip()
    try:
        parts = urllib.parse.urlsplit(url)
        host, _port = parts.hostname, parts.port      # .port raises ValueError unless it is 0-65535
    except ValueError:
        raise UsageError("--base-url is not a valid URL.") from None
    if parts.username or parts.password or parts.query or parts.fragment:
        raise UsageError("--base-url must not contain credentials, a query or a fragment. Put keys in an "
                         "environment variable and name it with --api-key-env.")
    if parts.scheme not in ("http", "https") or not host:
        raise UsageError("--base-url must start with https:// (or http:// for a server on this machine).")
    # urlsplit silently drops tabs and line breaks, and http.client can't send the rest; an IDN host is fine
    if any(c.isspace() or not c.isprintable() for c in url) or not parts.path.isascii():
        raise UsageError("--base-url contains a space, a control character or a non-ASCII character, perhaps an "
                         "invisible one from copying it. Type the URL again.")
    try:
        host.encode("idna")         # as the socket layer will: it fails on an empty or over-long label, as in a..b
    except UnicodeError:
        raise UsageError("--base-url has an invalid host name. Type the URL again.") from None
    if parts.scheme == "http" and sends_key and not is_loopback(host):
        raise UsageError(f"refusing to send an API key over plain http to {host}; use https.")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def build_provider(selection: Selection, *, on_retry=None) -> OpenAICompatProvider:
    return OpenAICompatProvider(selection.info, api_key=selection.api_key, auth_hint=selection.auth_hint,
                                on_retry=on_retry)


def provider_rows() -> list[tuple[str, str, str]]:
    """(name, key variable, default model) for help text, from the preset data."""
    return [(p.name, p.key_env, p.default_model) for p in (PRESETS[n] for n in sorted(PRESETS))]
