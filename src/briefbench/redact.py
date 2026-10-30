"""Keep API keys out of everything briefbench prints or logs. Vendor-neutral."""
import json
import re

REDACTED = "[redacted]"
MIN_SECRET = 8      # shorter values (placeholders for local servers) are not treated as secrets
MIN_FRAGMENT = 4
MASKED = r"[A-Za-z0-9_-]{0,64}\*{3,}[A-Za-z0-9_-]{0,64}"     # sk-bbFAK***9876, ****9876, xa***XX; bounded, so linear
_RUNS = re.compile(r"(?:\[redacted\]){2,}")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")   # C0 and C1 controls except \t and \n


def usable(secrets):
    return sorted({s for s in secrets if s and len(s) >= MIN_SECRET}, key=len, reverse=True)


def scrub(text, secrets):
    """Exact values only, plus their JSON-escaped form. Safe on user text and on JSON lines."""
    for s in usable(secrets):
        escaped = json.dumps(s)[1:-1]
        if escaped != s:
            text = text.replace(escaped, REDACTED)
        text = text.replace(s, REDACTED)
    return text


def redact_error(text, secrets):
    """Aggressive, for text from an endpoint or an exception: masked echoes, the full key,
    and any prefix or suffix of 4+ characters, in one pass so replacements are never re-scanned."""
    fragments = set()
    for s in usable(secrets):
        for n in range(MIN_FRAGMENT, len(s) + 1):
            fragments.update((s[:n], s[-n:]))
    alternatives = [MASKED] + [re.escape(f) for f in sorted(fragments, key=len, reverse=True)]
    text = re.sub("|".join(alternatives), REDACTED, text)
    return _RUNS.sub(REDACTED, text)


def strip_controls(text):
    """Remove terminal control characters (ESC included) from model-written text."""
    return _CONTROL.sub("", text)
