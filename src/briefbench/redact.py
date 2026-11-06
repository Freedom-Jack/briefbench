"""Keep key values and terminal control characters out of everything briefbench prints or logs. Vendor-neutral."""
import json
import re

REDACTED = "[redacted]"
MIN_SECRET = 8      # shorter values (placeholders) are not treated as secrets
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


def strip_controls(text):
    """Remove terminal control characters (ESC included) from text that a model or an agent wrote."""
    return _CONTROL.sub("", text)
