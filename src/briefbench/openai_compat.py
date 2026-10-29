"""The OpenAI-compatible Chat Completions wire format over stdlib urllib, with TLS from the OS trust store.

Speaks the protocol only: vendor differences arrive as data in ProviderInfo, and this module names
no vendor, host, key variable or model.
"""
from __future__ import annotations

import email.utils
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

import truststore

from . import __version__
from .errors import ProviderError
from .provider import Completion, Message, ProviderInfo, Usage
from .redact import redact_error

MAX_ATTEMPTS = 3
MAX_RETRY_WAIT_S = 30.0
MAX_BODY_BYTES = 10_000_000
USER_AGENT = f"briefbench/{__version__}"     # some CDN fronts answer 403 to urllib's default
_API_KEY_WORDS = re.compile(r"api[\s_-]?key", re.I)
_THINK = re.compile(r"\A\s*<think>.*?</think>\s*", re.S | re.I)
_SPACE = re.compile(r"\s+")


# ----------------------------------------------------------------------------- transport

@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]      # lower-cased names; only Retry-After is read; never logged
    body: bytes


class TransportError(Exception):
    """No HTTP status: timeout, TLS, DNS, refused, dropped connection, oversized body."""

    def __init__(self, kind: str, detail: str, *, retryable: bool = False):
        super().__init__(detail)
        self.kind, self.detail, self.retryable = kind, detail, retryable


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Stock urllib re-sends a redirected POST as a GET, with the Authorization header, to the new
    # host. Returning None makes every 3xx an HTTPError instead, and no second request is sent.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER: urllib.request.OpenerDirector | None = None


def _opener() -> urllib.request.OpenerDirector:
    global _OPENER
    if _OPENER is None:
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)   # CERT_REQUIRED and hostname checks stay on
        _OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), _NoRedirect())
    return _OPENER                                                 # ProxyHandler stays: HTTPS_PROXY is honoured


def post_json(url: str, headers: Mapping[str, str], payload: bytes, timeout: float) -> HttpResponse:
    request = urllib.request.Request(url, data=payload, headers=dict(headers), method="POST")
    try:
        with _opener().open(request, timeout=timeout) as response:
            return HttpResponse(response.status, _lower(response.headers), _read(response))
    except urllib.error.HTTPError as e:              # every non-2xx, refused redirects included
        try:
            body = _read(e)
        except (OSError, http.client.HTTPException):  # e.g. a timeout while reading the error body
            body = b""
        finally:
            e.close()
        return HttpResponse(e.code, _lower(e.headers), body)
    except urllib.error.URLError as e:               # raised while connecting or sending
        raise _classify(e.reason) from None
    except (OSError, http.client.HTTPException) as e:  # raised while waiting for or reading the reply
        raise _classify(e) from None


def _read(response) -> bytes:
    body = response.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        raise TransportError("bad_response", "the reply is larger than 10 MB")
    return body


def _lower(headers) -> dict[str, str]:
    return {k.lower(): v for k, v in (headers or {}).items()}


def _classify(exc) -> TransportError:
    if not isinstance(exc, BaseException):
        return TransportError("network", str(exc))
    if isinstance(exc, ssl.SSLCertVerificationError):
        return TransportError("tls", getattr(exc, "verify_message", None) or str(exc))
    if isinstance(exc, (ssl.SSLEOFError, ssl.SSLZeroReturnError)):
        return TransportError("dropped", "the TLS connection was closed", retryable=True)
    if isinstance(exc, ssl.SSLError):
        return TransportError("tls", str(exc))
    if isinstance(exc, TimeoutError):
        return TransportError("timeout", "timed out")
    if isinstance(exc, ConnectionRefusedError):
        return TransportError("refused", "connection refused")
    if isinstance(exc, socket.gaierror):
        return TransportError("dns", str(exc))
    if isinstance(exc, (ConnectionError, http.client.IncompleteRead)):   # resets, RemoteDisconnected, broken pipes
        return TransportError("dropped", type(exc).__name__, retryable=True)
    return TransportError("network", str(exc) or type(exc).__name__)


# ----------------------------------------------------------------------------- provider

class OpenAICompatProvider:
    def __init__(self, info: ProviderInfo, *, api_key: str | None = None, auth_hint: str = "",
                 transport: Callable[..., HttpResponse] = post_json, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, on_retry: Callable[[str], None] | None = None):
        self.info = info
        self._key, self._auth_hint = api_key, auth_hint
        self._transport, self._sleep, self._clock, self._on_retry = transport, sleep, clock, on_retry
        base = info.base_url
        self._url = base if base.endswith("/chat/completions") else base + "/chat/completions"
        parts = urllib.parse.urlsplit(self._url)
        self._host, self._hostname = parts.netloc, parts.hostname or ""

    def body(self, messages: Sequence[Message], max_output_tokens: int) -> dict[str, Any]:
        return {"model": self.info.model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                self.info.token_param: max_output_tokens,
                **self.info.params}

    def preview(self, messages, *, max_output_tokens):
        headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT}
        if self.info.key_env:
            headers["Authorization"] = f"Bearer ${self.info.key_env}"
        return {"url": self._url, "headers": headers, "body": self.body(messages, max_output_tokens)}

    def complete(self, messages, *, max_output_tokens):
        payload = json.dumps(self.body(messages, max_output_tokens)).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        start = self._clock()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._transport(self._url, headers, payload, self.info.timeout_s)
            except TransportError as e:
                if e.retryable and attempt < MAX_ATTEMPTS:
                    self._pause("the connection dropped", float(2 ** (attempt - 1)), attempt)
                    continue
                raise ProviderError("network" if e.kind in ("refused", "dns", "dropped") else e.kind,
                                    self._transport_message(e, attempt), attempts=attempt,
                                    latency_ms=self._elapsed(start)) from None
            if 200 <= response.status < 300:
                return self._parse(response.body, attempt, self._elapsed(start))
            wait = self._retry_wait(response, attempt)
            if wait is None:
                raise self._http_error(response, attempt, self._elapsed(start))
            self._pause(f"HTTP {response.status}", wait, attempt)
        raise AssertionError("unreachable")

    # -- retries

    def _retry_wait(self, response: HttpResponse, attempt: int) -> float | None:
        status = response.status
        if attempt >= MAX_ATTEMPTS or not (status in (408, 409, 429) or status >= 500):
            return None
        if status == 429 and _is_quota(response.body):
            return None
        after = retry_after_seconds(response.headers.get("retry-after"))
        if after is not None:
            return after if after <= MAX_RETRY_WAIT_S else None
        return float(2 ** (attempt - 1))                  # 1 s, then 2 s

    def _pause(self, what: str, wait: float, attempt: int) -> None:
        if self._on_retry:
            self._on_retry(f"{what} from {self._host}; retrying in {wait:.0f} s "
                           f"(attempt {attempt + 1} of {MAX_ATTEMPTS})")
        self._sleep(wait)

    def _elapsed(self, start: float) -> int:
        return round((self._clock() - start) * 1000)

    # -- errors

    def _redact(self, text: str) -> str:
        return redact_error(text, [self._key] if self._key else [])

    def _http_error(self, response: HttpResponse, attempts: int, latency_ms: int) -> ProviderError:
        status, info, host = response.status, self.info, self._host
        raw = error_message(response.body)
        detail = self._redact(raw) or "no error message"
        tries = f" after {attempts} attempts" if attempts > 1 else ""

        def err(kind: str, message: str) -> ProviderError:
            return ProviderError(kind, message, status=status, attempts=attempts, latency_ms=latency_ms)

        if status in (401, 403) or (status == 400 and _API_KEY_WORDS.search(raw)):
            # Auth error bodies can echo key fragments, so the body is never shown.
            if not self._key:
                return err("auth", f"{host} requires an API key (HTTP {status}). Name the variable that holds "
                                   "it with --api-key-env.")
            if status == 403:
                message = (f"{info.name} refused the request (HTTP 403). Check that the key in {info.key_env} "
                           f"is valid and may use the model {info.model!r}.")
            else:
                message = f"{info.name} rejected the API key in {info.key_env} (HTTP {status})."
            return err("auth", message + (f" {self._auth_hint}" if self._auth_hint else ""))
        if 300 <= status < 400:
            return err("redirect", f"{host} answered with a redirect (HTTP {status}). briefbench doesn't follow "
                                   "redirects, so your key is never sent to another host; use the final URL "
                                   "as --base-url.")
        if status == 404:
            message = (f"HTTP 404 from {host}: {detail}. Check the model id {info.model!r} and the base URL "
                       f"{info.base_url}.")
            if info.chosen_by.startswith("auto"):
                message += f" ({info.name} was chosen because {info.key_env} is set; pick another with --provider.)"
            return err("not_found", message)
        if status == 429 and _is_quota(response.body):
            return err("quota", f"{info.name} says the account is out of quota or credit (HTTP 429): {detail}")
        if status == 429:
            wait = retry_after_seconds(response.headers.get("retry-after"))
            if wait is not None and wait > MAX_RETRY_WAIT_S and attempts < MAX_ATTEMPTS:
                return err("rate_limit", f"{host} is rate-limiting requests (HTTP 429) and asks to wait "
                                         f"{wait:.0f} s, longer than briefbench waits: {detail}")
            return err("rate_limit", f"{host} is rate-limiting requests (HTTP 429){tries}: {detail}")
        if status in (408, 409) or status >= 500:
            return err("server", f"HTTP {status} from {host}{tries}: {detail}")
        return err("bad_request", f"HTTP {status} from {host}: {detail}")

    def _transport_message(self, e: TransportError, attempts: int) -> str:
        host, detail = self._host, self._redact(e.detail)
        if e.kind == "timeout":
            return f"No response from {host} within {self.info.timeout_s:g} s. Try again, or raise --timeout."
        if e.kind == "tls":
            return (f"The TLS certificate of {host} failed verification against your operating system's trust "
                    f"store ({detail}). briefbench never turns verification off; on a network that inspects "
                    "TLS, the operating system must trust the network's root certificate.")
        if e.kind == "refused":
            return f"Could not connect to {host} (connection refused)." + (
                " Is the server running?" if is_loopback(self._hostname) else "")
        if e.kind == "dns":
            return f"Could not find the host {self._hostname}. Check the network and --base-url."
        if e.kind == "dropped":
            return f"{host} closed the connection" + (f" {attempts} times." if attempts > 1 else ".")
        if e.kind == "bad_response":
            return f"{self.info.name} returned something that is not a chat completion ({detail})."
        return f"Network error talking to {host}: {detail}."

    # -- parsing

    def _parse(self, body: bytes, attempts: int, latency_ms: int) -> Completion:
        def bad(what: str) -> ProviderError:
            return ProviderError("bad_response", f"{self.info.name} returned something that is not a chat "
                                 f"completion ({what}). Check --base-url.", attempts=attempts, latency_ms=latency_ms)

        try:
            data = json.loads(body)
        except ValueError:
            raise bad("not JSON") from None
        if not isinstance(data, dict):
            raise bad("not a JSON object")
        if data.get("error"):
            raise bad("an error object: " + (self._redact(error_message(body)) or "no message"))
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise bad("no choices")
        choice = choices[0]
        if choice.get("error"):                                   # some gateways put errors here
            raise bad("an error inside the reply: " + self._redact(_message_of(choice["error"])))
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        text, unclosed_think = visible_text(message.get("content"))
        reasoning = any(_has_content(message.get(k)) for k in ("reasoning", "reasoning_content", "reasoning_details"))
        finish = choice.get("finish_reason")
        return Completion(
            text=text,
            finish_reason=finish.lower() if isinstance(finish, str) else None,
            model_reported=_str(data.get("model")),
            response_id=_str(data.get("id")),
            system_fingerprint=_str(data.get("system_fingerprint")),
            refusal=_str(message.get("refusal")),
            reasoning_only=not text.strip() and (reasoning or unclosed_think),
            usage=normalize_usage(data.get("usage")),
            latency_ms=latency_ms,
            attempts=attempts,
        )


# ----------------------------------------------------------------------------- helpers

def visible_text(content) -> tuple[str, bool]:
    """(text, unclosed_think). Keeps text chunks only; strips one leading <think> block."""
    if isinstance(content, list):          # chunked content (e.g. reasoning on): keep the text chunks
        content = "".join(p["text"] for p in content if isinstance(p, dict)
                          and p.get("type") in ("text", "output_text") and isinstance(p.get("text"), str))
    if not isinstance(content, str):       # null or anything else
        return "", False
    text = _THINK.sub("", content, count=1)
    if text.lstrip()[:7].lower() == "<think>":    # never closed: all reasoning, no answer
        return "", True
    return text, False


def normalize_usage(raw) -> Usage:
    if not isinstance(raw, dict):
        return Usage()
    details = raw.get("completion_tokens_details")
    return Usage(_int(raw.get("prompt_tokens")), _int(raw.get("completion_tokens")),
                 _int(details.get("reasoning_tokens")) if isinstance(details, dict) else None, raw)


def error_message(body: bytes) -> str:
    """The first message in any known error shape, on one line, at most 300 characters:
    {error:{message}}, a JSON array of those, {error:"..."}, {detail:...}, {message:...}, or plain
    text. presets.py notes which vendor uses which shape."""
    try:
        data = json.loads(body)
    except ValueError:
        text = body.decode("utf-8", "replace")
    else:
        if isinstance(data, list) and data:
            data = data[0]
        text = _message_of(data) if isinstance(data, dict) else body.decode("utf-8", "replace")
    return _SPACE.sub(" ", text).strip()[:300]


def _message_of(obj) -> str:
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return json.dumps(obj)
    err = obj.get("error")
    msg = err.get("message") if isinstance(err, dict) else err
    if msg is None:
        msg = obj.get("detail") or obj.get("message")
    if msg is None:
        return json.dumps(obj)
    return msg if isinstance(msg, str) else json.dumps(msg)


def _is_quota(body: bytes) -> bool:
    try:
        data = json.loads(body)
    except ValueError:
        return False
    if isinstance(data, list) and data:
        data = data[0]
    err = data.get("error") if isinstance(data, dict) else None
    return isinstance(err, dict) and "insufficient_quota" in (err.get("code"), err.get("type"))


def retry_after_seconds(value: str | None, now: datetime | None = None) -> float | None:
    """Retry-After as seconds or as an HTTP date; None when absent or unreadable."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - (now or datetime.now(timezone.utc))).total_seconds())


def is_loopback(host: str) -> bool:
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _has_content(value) -> bool:
    return bool(value.strip()) if isinstance(value, str) else bool(value)


def _str(value) -> str | None:
    return value if isinstance(value, str) else None


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
