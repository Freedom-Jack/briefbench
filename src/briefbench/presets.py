"""Vendor-specific settings: the only module that names vendors, their agent CLIs, the folders those CLIs use or
their key variables. The rest of briefbench runs an agent CLI through an `Agent`, without knowing which one.

Flags were checked on 2026-11-03 against Claude Code 2.1.309 and Codex 0.166 (docs/design.md, "Sources"). The
asker role, added on 2026-11-05, reuses the rewriter's read-only tools and the judge's schema flags.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
from dataclasses import dataclass
from typing import Callable, Mapping

from .redact import MIN_SECRET

# briefbench never uses these. It removes them from every agent CLI's environment, so the CLI runs on your
# subscription login instead of billing an API account, and it scrubs their values from what it prints and logs.
KEY_ENVS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CODEX_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
            "OPENAI_API_KEY")
# Also removed: what would send a CLI to another endpoint or billing account, and the marks of a Claude Code
# session that briefbench may itself be running in. A token from `claude setup-token` is a plan login, so it stays.
_ROUTING = ("ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "CLAUDECODE")
_KEEP = ("CLAUDE_CODE_OAUTH_TOKEN",)
SKILL_DIRS = ("~/.claude/skills/brief", "~/.agents/skills/brief")    # where `brief` looks, in order
_SLOT = re.compile(r"\{(\w+)\}")


def secret_values(environ: Mapping[str, str]) -> list[str]:
    """The values of the key variables that are set. Shorter ones, such as placeholders, are ignored."""
    values = ((environ.get(name) or "").strip() for name in KEY_ENVS)
    return [v for v in values if len(v) >= MIN_SECRET]


def agent_env(environ: Mapping[str, str]) -> dict[str, str]:
    """The environment an agent CLI runs in: yours, minus API keys and anything that reroutes its billing."""
    return {k: v for k, v in environ.items() if k not in KEY_ENVS and k not in _ROUTING
            and (not k.startswith("CLAUDE_CODE_") or k in _KEEP)}


@dataclass(frozen=True)
class Reply:
    text: str               # the agent's final message
    tokens: int | None      # input and output tokens, cached ones included, when the CLI reports them
    model: str | None       # the model that answered, when the CLI reports it
    error: str | None       # what went wrong, when the CLI says the run failed


@dataclass(frozen=True)
class Agent:
    """One agent CLI. Role templates are arguments after the executable, with {prompt}, {model}, {check},
    {schema} (a JSON Schema file) and {schema_json} (its text) slots. An argument that starts with "?" is left
    out unless every slot in it has a value. There is no shell, so nothing needs quoting."""

    name: str
    vendor: str
    commands: tuple[str, ...]                 # executable names, looked up on PATH
    bundled: tuple[str, ...]                  # copies that come with a desktop app, as globs; the newest wins
    login: tuple[str, ...]                    # arguments that report the login
    on_plan: Callable[[str], bool]            # that report -> logged in with a subscription
    login_fix: str
    roles: Mapping[str, tuple[str, ...]]      # worker, rewriter, asker (the skill's questions), judge
    parse: Callable[[str], Reply]             # stdout -> Reply
    default_model: str = ""                   # "" leaves the model to the CLI

    def find(self) -> str | None:
        for name in self.commands:
            if found := shutil.which(name):
                return found
        copies = [p for pattern in self.bundled for p in glob.glob(os.path.expanduser(pattern))]
        return max(copies, key=_natural) if copies else None

    def argv(self, executable: str, role: str, **slots: str) -> list[str]:
        out = [executable]
        for arg in self.roles[role]:
            optional, arg = arg.startswith("?"), arg.removeprefix("?")
            names = _SLOT.findall(arg)
            if optional and not all(slots.get(n) for n in names):
                continue
            out.append(_SLOT.sub(lambda m: slots.get(m.group(1), ""), arg) if names else arg)
        return out


def _natural(path: str) -> list:
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", path)]


def _int(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _claude_reply(stdout: str) -> Reply:
    data = None
    for line in reversed(stdout.strip().splitlines()):       # --output-format json prints one result object
        try:
            data = json.loads(line)
            break
        except ValueError:
            continue
    if not isinstance(data, dict):
        return Reply("", None, None, "no JSON result on stdout")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    tokens = sum(_int(usage.get(k)) for k in ("input_tokens", "cache_creation_input_tokens",
                                               "cache_read_input_tokens", "output_tokens"))
    models = data.get("modelUsage") if isinstance(data.get("modelUsage"), dict) else {}
    model = max(models, key=lambda m: _int((models[m] or {}).get("outputTokens"))) if models else None
    found = data.get("structured_output")
    text = json.dumps(found) if found is not None else str(data.get("result") or "")
    return Reply(text, tokens or None, model, str(data.get("subtype") or "error") if data.get("is_error") else None)


def _codex_reply(stdout: str) -> Reply:
    text, tokens, error = "", 0, None
    for line in stdout.splitlines():                          # --json prints one event per line
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, item = event.get("type"), event.get("item") or {}
        if kind == "item.completed" and item.get("type") == "agent_message":
            text = str(item.get("text") or "")
        elif kind == "turn.completed":
            usage = event.get("usage") or {}
            tokens += _int(usage.get("input_tokens")) + _int(usage.get("output_tokens"))   # cached are inside input
        elif kind in ("turn.failed", "error"):
            error = str((event.get("error") or {}).get("message") or event.get("message") or kind)
    return Reply(text, tokens or None, None, error)


def _claude_on_plan(report: str) -> bool:
    try:
        status = json.loads(report)
    except ValueError:
        return False
    method = str(status.get("authMethod") or "").lower()
    return status.get("loggedIn") is True and not any(word in method for word in ("api", "console"))


AGENTS: dict[str, Agent] = {a.name: a for a in (
    Agent("claude-code", "anthropic", ("claude",),
          ("~/Library/Application Support/Claude/claude-code/*/*/claude.app/Contents/MacOS/claude",),
          ("auth", "status"), _claude_on_plan,
          "Run `claude auth login --claudeai` in a terminal, to log in with your Claude plan.",
          {"worker": ("-p", "--output-format", "json", "--permission-mode", "acceptEdits", "--permission-prompts",
                      "none", "?--allowedTools=Bash({check}:*)", "--no-session-persistence", "?--model={model}",
                      "--", "{prompt}"),
           "rewriter": ("-p", "--output-format", "json", "--tools", "Read,Grep,Glob", "--permission-prompts", "none",
                        "--disable-slash-commands", "--no-session-persistence", "?--model={model}", "--", "{prompt}"),
           "asker": ("-p", "--output-format", "json", "--tools", "Read,Grep,Glob", "--json-schema", "{schema_json}",
                     "--permission-prompts", "none", "--disable-slash-commands", "--no-session-persistence",
                     "?--model={model}", "--", "{prompt}"),
           "judge": ("-p", "--output-format", "json", "--tools", "", "--json-schema", "{schema_json}",
                     "--disable-slash-commands", "--no-session-persistence", "?--model={model}", "--", "{prompt}")},
          _claude_reply, default_model="claude-opus-5-5"),
    Agent("codex", "openai", ("codex",),
          ("/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex",),
          ("login", "status"), lambda report: "chatgpt" in report.lower(),
          "Open the ChatGPT app, or run `codex login`, and sign in with ChatGPT rather than an API key.",
          {"worker": ("exec", "--json", "--ephemeral", "-s", "workspace-write", "?--model={model}", "--", "{prompt}"),
           "rewriter": ("exec", "--json", "--ephemeral", "-s", "read-only", "?--model={model}", "--", "{prompt}"),
           "asker": ("exec", "--json", "--ephemeral", "-s", "read-only", "--output-schema", "{schema}",
                     "?--model={model}", "--", "{prompt}"),
           "judge": ("exec", "--json", "--ephemeral", "-s", "read-only", "--skip-git-repo-check", "--output-schema",
                     "{schema}", "?--model={model}", "--", "{prompt}")},
          _codex_reply),
)}
