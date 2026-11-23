"""Vendor-specific settings: the only module that names vendors, their agent CLIs, the folders those CLIs use or
their key variables. The rest of briefbench runs an agent CLI through an `Agent`, without knowing which one.

Flags were checked on 2026-11-03 against Claude Code 2.1.309 and Codex 0.166 (docs/design.md, "Sources"). The
asker role, added on 2026-11-05, reuses the rewriter's read-only tools and the judge's schema flags. On 2026-11-06 a task-worker
role was added, checked against Claude Code 2.1.317: the worker of experiments scored by the check alone, confined so
it can't read the answer key, the records or the other arm. Its stream-json output ends with the same result object
that json prints, so one parser reads both. On 2026-11-09 each arm got its own temporary folder, checked live against
2.1.317: before, both arms' sandboxes used the one temporary folder that every Claude Code session on the machine
shares, and in one pilot trial an arm ran a script the other had just written there. On 2026-11-10 came the stand-in
requester (answerer), which answers a skill's questions from a task file's facts, and confined forms of the skill's
two headless calls for task files (task-asker, task-rewriter).
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path
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
# Where agent CLIs keep other sessions' transcripts and scratch files on this machine, which can hold a study's seed or
# answers: an arm of a task-file trial may not read them. {uid} is your user id. /tmp/claude-{uid} is the temporary
# folder that Claude Code sessions share; a task worker gets a folder of its own instead (Agent.temp_env).
PRIVATE_PLACES = ("~/.claude/projects", "~/.codex/sessions", "/tmp/claude-{uid}", "/private/tmp/claude-{uid}")
# Claude Code's sandbox for the task-worker, checked against 2.1.317 on 2026-11-06: every shell command is allowed and
# runs inside an OS sandbox that confines writes to the working folder and the arm's own temporary folder, and blocks
# reads of the {deny} folders (the data folder, the keys, the other arm's folders, the bench's own source and
# PRIVATE_PLACES), for the Read tool as well. It fails closed if the sandbox can't start.
# Allowing Bash outright matters: without it, commands Claude Code can't analyse, such as `cat > $TMPDIR/x <<EOF`, still
# asked for approval, which nobody can give in a headless run, and were denied.
_SANDBOX = ('{"sandbox": {"enabled": true, "autoAllowBashIfSandboxed": true, "failIfUnavailable": true, '
            '"allowUnsandboxedCommands": false, "filesystem": {"denyRead": {deny}}}, '
            '"permissions": {"allow": ["Bash"], "deny": {deny_rules}}}')
# The skill's two headless calls in a task-file trial, added 2026-11-10: their replies, the questions and the brief,
# reach an arm, so they are kept from reading the same {deny_rules} places as the worker. They have only the file tools,
# whose reads Claude Code checks against Read rules (for Grep and Glob, as its docs say, as best it can), and their
# steps come back as stream-json, which the bench scans like the worker's.
_READ_DENY = '{"permissions": {"deny": {deny_rules}}}'
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
    usage: dict | None = None  # disjoint token counts; unknown stays null
    cost_usd: float | None = None  # CLI estimate, not a subscription bill


@dataclass(frozen=True)
class Agent:
    """One agent CLI. Role templates are arguments after the executable, with {prompt}, {model}, {check},
    {schema} (a JSON Schema file), {schema_json} (its text), {deny} (a JSON list of folders the worker may not read)
    and {deny_rules} (the same as permission rules) slots. An argument that starts with "?" is left out unless every
    slot in it has a value. There is no shell, so nothing needs quoting. confines_reads says whether its task-worker
    can be kept from reading the {deny} folders; one that can't doesn't run experiments scored by the check alone."""

    name: str
    vendor: str
    commands: tuple[str, ...]                 # executable names, looked up on PATH
    bundled: tuple[str, ...]                  # copies that come with a desktop app, as globs; the newest wins
    login: tuple[str, ...]                    # arguments that report the login
    on_plan: Callable[[str], bool]            # that report -> logged in with a subscription
    login_fix: str
    # worker, rewriter, asker (the skill's questions) and judge; for task files task-worker, task-asker and
    # task-rewriter, kept out of the {deny} places, and answerer, the stand-in requester, with no tools
    roles: Mapping[str, tuple[str, ...]]
    parse: Callable[[str], Reply]             # stdout -> Reply
    default_model: str = ""                   # "" leaves the model to the CLI
    confines_reads: bool = False              # its task-worker can be kept out of the {deny} folders
    # The variable that moves the CLI's own temporary folder, set to a folder of each arm's own. It needs a short path:
    # given a long one, Claude Code 2.1.317 falls back to the shared /tmp/claude-{uid} (checked on 2026-11-09).
    temp_env: str = ""
    # stdout -> what the agent did and said, for the scan for forbidden folders: what the CLI says of itself goes, such
    # as its start-up report, which names the arm's own memory folder under ~/.claude/projects.
    actions: Callable[[str], str] = lambda stdout: stdout
    message: Callable[[str], str] | None = None  # prompt -> one input line for a conversation
    turn_done: Callable[[str], bool] | None = None
    session: Callable | None = None            # optional stateful wire protocol, owned by the preset
    slots: Callable | None = None              # derived, host-specific command slots
    session_version: str = ""                 # frozen with experiments that use a stateful protocol

    def find(self) -> str | None:
        for name in self.commands:
            if found := shutil.which(name):
                return found
        copies = [p for pattern in self.bundled for p in glob.glob(os.path.expanduser(pattern))]
        return max(copies, key=_natural) if copies else None

    def argv(self, executable: str, role: str, **slots: str) -> list[str]:
        if self.slots:
            slots |= self.slots(role, slots)
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


# Claude Code's notice, as a tool's whole result, that the output was too large, so it saved it in the session's own
# folder: "<persisted-output>\nOutput too large (47.3KB). Full output saved to: ~/.claude/projects/<folder>/<session>/
# tool-results/<tool call>.txt\n\nPreview (first 2KB): ...", as 2.1.321 printed it in round 1 (2026-11-11).
_SAVED = re.compile(r"^(.*saved to: )(/.+)$", re.M)


def _claude_actions(stdout: str) -> str:
    """stream-json without what the CLI says of itself. Its start-up report goes (type system, subtype init): it lists
    the session's own folders, among them its memory folder under ~/.claude/projects, before the agent has done
    anything. So does the path in its notice that it saved a tool's large output in the session's own folder there:
    in round 1 that notice flagged six trials, though no call opened the file (fixed 2026-11-14). The rest of the
    notice stays, and the path still counts wherever else it appears, as when the agent reads the file."""
    kept = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            event = None
        if not isinstance(event, dict):
            kept.append(line)
        elif not (event.get("type") == "system" and event.get("subtype") == "init"):
            kept.append(json.dumps(event, ensure_ascii=False) if _unsaved(event) else line)
    return "\n".join(kept)


def _unsaved(event: dict) -> bool:
    """Takes the path out of the CLI's saved-output notices in this event's tool results, in place, and says whether
    it found one. A notice is a tool result that starts with <persisted-output>, and only its own file's path goes: in
    the session's tool-results folder, named after the tool call whose result the notice is."""
    message, session, found = event.get("message"), event.get("session_id"), False
    content = message.get("content") if isinstance(message, dict) else None
    if event.get("type") != "user" or not isinstance(content, list) or not session or not isinstance(session, str):
        return False
    for block in content:
        call = block.get("tool_use_id") if isinstance(block, dict) and block.get("type") == "tool_result" else None
        if not call or not isinstance(call, str):
            continue
        # The CLI can save under its parent session's UUID. The tool call id still identifies this result.
        own = re.compile(rf"/\.claude/projects/[^/]+/[^/]+/tool-results/{re.escape(call)}(\.\w+)?$")
        inner = block.get("content")             # the result's text, or a list of parts
        texts = ([(block, "content")] if isinstance(inner, str)
                 else [(p, "text") for p in (inner if isinstance(inner, list) else []) if isinstance(p, dict)])
        for holder, key in texts:
            text = holder.get(key)
            if isinstance(text, str) and text.startswith("<persisted-output>"):
                holder[key] = _SAVED.sub(lambda m: m.group(1) + "[the CLI's own file]" if own.search(m.group(2))
                                         else m.group(0), text)
                found = found or holder[key] != text
    return found


def _claude_reply(stdout: str) -> Reply:
    """json prints one result object; stream-json prints events and then the same result object. A run cut off before
    its result, at the timeout or by a crash, has no result: that is an error, whatever came before it."""
    data = None
    for line in reversed(stdout.strip().splitlines()):
        try:
            found = json.loads(line)
        except ValueError:
            continue
        if isinstance(found, dict) and found.get("type", "result") == "result":     # every stream event has a type
            data = found
            break
    if not isinstance(data, dict):
        return Reply("", None, None, "no JSON result on stdout")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    tokens = sum(_int(usage.get(k)) for k in ("input_tokens", "cache_creation_input_tokens",
                                               "cache_read_input_tokens", "output_tokens"))
    models = data.get("modelUsage") if isinstance(data.get("modelUsage"), dict) else {}
    model = max(models, key=lambda m: _int((models[m] or {}).get("outputTokens"))) if models else None
    found = data.get("structured_output")
    text = json.dumps(found) if found is not None else str(data.get("result") or "")
    detail = {"input": _int(usage.get("input_tokens")), "cache_write": _int(usage.get("cache_creation_input_tokens")),
              "cache_read": _int(usage.get("cache_read_input_tokens")), "output": _int(usage.get("output_tokens"))}
    cost = data.get("total_cost_usd")
    return Reply(text, tokens or None, model, _claude_error(data) if data.get("is_error") else None,
                 detail if usage else None, cost if type(cost) in (float, int) else None)


def _claude_error(data: dict) -> str:
    """A failed run's own message: its result text, or an error subtype's errors, after the HTTP status of an API
    error, such as "HTTP 429: You've hit your usage limit ...". The subtype alone says little: in round 1 a usage
    limit ended with subtype success (2.1.321, 2026-11-11), so before 2026-11-14 the bench reported "(success)"."""
    errors = data.get("errors") if isinstance(data.get("errors"), list) else []
    said = (str(s).strip() for s in [data.get("result") or "", *errors])
    message = "; ".join(dict.fromkeys(s for s in said if s))
    status, subtype = data.get("api_error_status"), str(data.get("subtype") or "")
    label = f"HTTP {status}" if _int(status) else "" if subtype == "success" else subtype
    return f"{label}: {message}" if label and message else message or label or "error"


def _codex_reply(stdout: str) -> Reply:
    text, tokens, error = "", 0, None
    detail = None
    complete, session_usage = False, None
    for line in stdout.splitlines():                          # --json or the session's JSON-RPC notifications
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, item = event.get("type"), event.get("item") or {}
        method, params = event.get("method"), event.get("params") or {}
        if method == "item/completed" and params.get("item", {}).get("type") == "agentMessage":
            text = params["item"].get("text", "")
        elif method == "thread/tokenUsage/updated":
            session_usage = (params.get("tokenUsage") or {}).get("total")
        elif method == "turn/completed":
            turn = params.get("turn") or {}
            complete = turn.get("status") == "completed"
            if not complete:
                error = (turn.get("error") or {}).get("message") or "interview turn did not complete"
        elif event.get("error") and "id" in event:
            error = str(event["error"].get("message") or "session request failed")
        if kind == "item.completed" and item.get("type") == "agent_message":
            text = str(item.get("text") or "")
        elif kind == "turn.completed":
            complete = True
            usage = event.get("usage") or {}
            tokens += _int(usage.get("input_tokens")) + _int(usage.get("output_tokens"))   # cached are inside input
            detail = detail or dict.fromkeys(("input", "cache_write", "cache_read", "output"), 0)
            cached = _int(usage.get("cached_input_tokens"))
            detail["input"] += _int(usage.get("input_tokens")) - cached
            detail["cache_read"] += cached
            detail["output"] += _int(usage.get("output_tokens"))
        elif kind in ("turn.failed", "error"):
            error = str((event.get("error") or {}).get("message") or event.get("message") or kind)
    if session_usage:
        cached, written = _int(session_usage.get("cachedInputTokens")), _int(session_usage.get("cacheWriteInputTokens"))
        detail = {"input": _int(session_usage.get("inputTokens")) - cached - written,
                  "cache_write": written, "cache_read": cached, "output": _int(session_usage.get("outputTokens"))}
        tokens = sum(detail.values())
    if not complete and not error:
        error = "no completed turn on stdout"
    return Reply(text, tokens or None, None, error, detail)


# Check-scored roles use an explicit allowlist of readable runtime paths and their own workspace/temp.
# No user configuration, skills, plugins, memories, MCP tools or proactive delegation enter a task.
_CODEX_CONFIG = ('model_reasoning_effort="medium"', 'forced_login_method="chatgpt"', 'approval_policy="never"',
                 'model_provider="openai"', 'web_search="disabled"', 'project_doc_max_bytes=0', 'notify=[]',
                 'skills.bundled.enabled=false', 'skills.include_instructions=false', 'tools.update_plan.enabled=false',
                 'features.skip_host_skill_discovery=true', 'features.skill_search=false', 'features.plugins=false',
                 'features.apps=false', 'features.memories=false', 'features.hooks=false',
                 'features.multi_agent=false', 'features.multi_agent_v2=false', 'features.shell_snapshot=false',
                 'features.view_image=false', 'features.image_generation=false', 'features.workspace_dependencies=false',
                 'features.sleep_tool=false')
_CODEX_FLAGS = tuple(arg for value in _CODEX_CONFIG for arg in ("-c", value))
_CODEX_CONFINED = (*_CODEX_FLAGS, "-c", 'default_permissions="briefbench"', "-c",
                   "permissions.briefbench={permission_profile}", "-c", "mcp_servers={disabled_servers}")
_CODEX_EXEC = ("exec", "--json", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config")


def _codex_slots(role, slots):
    if not (role.startswith("task-") or role == "answerer"):
        return {}
    mode = "write" if role == "task-worker" else "read"
    fs = {":root": "deny", ":minimal": "read", "/Library": "read", "/private/var/db": "read",
          ":workspace_roots": {".": mode, **{p: "read" for p in (".git", ".agents", ".codex", ".aws")}}}
    if temp := slots.get("temp"):
        fs[temp] = "write"
    denied = slots.get("deny") or "[]"
    for path in ["{deny}"] if denied == "{deny}" else json.loads(denied):
        fs[path] = "deny"

    def toml(value):
        return ("{" + ",".join(json.dumps(k) + "=" + toml(v) for k, v in value.items()) + "}"
                if isinstance(value, dict) else json.dumps(value))
    # The app server has no --ignore-user-config flag. Disable every configured MCP server explicitly there too.
    path = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml"
    config = tomllib.loads(path.read_text()) if role == "task-interviewer" and path.is_file() else {}
    servers = {name: {"enabled": False} for name in config.get("mcp_servers", {})}
    return {"permission_profile": toml({"filesystem": fs, "network": {"enabled": False}}),
            "disabled_servers": toml(servers)}


class _CodexSession:
    """One ephemeral thread over the subscription CLI's stdio app server; no SDK or paid API client."""
    def __init__(self, cwd, slots):
        self.cwd, self.schema = str(cwd), json.loads(slots["schema_json"])
        self.thread, self.serial, self.prompt = None, 0, None

    def request(self, method, params):
        self.serial += 1
        return json.dumps({"id": self.serial, "method": method, "params": params})

    def turn(self):
        return self.request("turn/start", {"threadId": self.thread, "input": [{"type": "text", "text": self.prompt}],
                                            "effort": "medium", "outputSchema": self.schema})

    def message(self, prompt):
        self.prompt = prompt
        return [self.turn() if self.thread else self.request("initialize", {
            "clientInfo": {"name": "briefbench", "version": "1"}, "capabilities": {"experimentalApi": True}})]

    def receive(self, line):
        event = json.loads(line)
        if event.get("id") == 1 and "result" in event:
            return [json.dumps({"method": "initialized"}), self.request("thread/start", {
                "cwd": self.cwd, "runtimeWorkspaceRoots": [self.cwd], "ephemeral": True,
                "approvalPolicy": "never", "permissions": "briefbench",
                "allowProviderModelFallback": False})]
        if event.get("id") == 2 and "result" in event:
            result = event["result"]
            if result.get("approvalPolicy") != "never" or (result.get("activePermissionProfile") or {}).get("id") != "briefbench":
                raise ValueError("the requested confined permission profile was not applied")
            self.thread = result["thread"]["id"]
            return [self.turn()]
        if "method" in event and "id" in event:
            return [json.dumps({"id": event["id"], "error": {"code": -32601, "message": "Unattended requests are refused"}})]
        return []


def _codex_turn_done(line):
    try:
        event = json.loads(line)
        return event.get("method") == "turn/completed" or ("id" in event and "error" in event)
    except (ValueError, AttributeError):
        return False


def _codex_actions(stdout):
    # RPC startup replies include internal paths; retain all actual actions, outputs and errors for the scan.
    kept = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            kept.append(line)
            continue
        if "method" in event or "error" in event or "type" in event:
            kept.append(line)
    return "\n".join(kept)


def _claude_turn_done(line: str) -> bool:
    try:
        return json.loads(line).get("type") == "result"
    except (ValueError, AttributeError):
        return False


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
           # For experiments scored by the check alone: any shell command, inside the sandbox, never the check;
           # each step in the output (stream-json), so the bench can scan it; no MCP servers, which run outside the
           # sandbox; and none of your user-level settings, which could loosen it. Checked live against 2.1.317.
           "task-worker": ("-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
                           "--tools", "Bash,Read,Edit,Write", "--disable-slash-commands", "--effort", "medium",
                           "--permission-prompts", "none", "--settings", _SANDBOX, "--strict-mcp-config",
                           "--setting-sources", "project,local", "--no-session-persistence", "?--model={model}",
                           "--", "{prompt}"),
           "rewriter": ("-p", "--output-format", "json", "--tools", "Read,Grep,Glob", "--permission-prompts", "none",
                        "--disable-slash-commands", "--no-session-persistence", "?--model={model}", "--", "{prompt}"),
           "asker": ("-p", "--output-format", "json", "--tools", "Read,Grep,Glob", "--json-schema", "{schema_json}",
                     "--permission-prompts", "none", "--disable-slash-commands", "--no-session-persistence",
                     "?--model={model}", "--", "{prompt}"),
           "judge": ("-p", "--output-format", "json", "--tools", "", "--json-schema", "{schema_json}",
                     "--disable-slash-commands", "--no-session-persistence", "?--model={model}", "--", "{prompt}"),
           "task-asker": ("-p", "--output-format", "stream-json", "--verbose", "--tools", "Read,Grep,Glob",
                          "--json-schema", "{schema_json}", "--permission-prompts", "none", "--settings", _READ_DENY,
                          "--strict-mcp-config", "--setting-sources", "project,local", "--disable-slash-commands",
                          "--no-session-persistence", "?--model={model}", "--", "{prompt}"),
           "task-interviewer": ("-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
                                "--tools", "Read,Grep,Glob", "--json-schema", "{schema_json}", "--effort", "medium",
                                "--permission-prompts", "none", "--settings", _READ_DENY, "--strict-mcp-config",
                                "--setting-sources", "project,local", "--disable-slash-commands",
                                "--no-session-persistence", "?--model={model}"),
           "task-rewriter": ("-p", "--output-format", "stream-json", "--verbose", "--tools", "Read,Grep,Glob",
                             "--permission-prompts", "none", "--settings", _READ_DENY, "--strict-mcp-config",
                             "--setting-sources", "project,local", "--disable-slash-commands",
                             "--no-session-persistence", "?--model={model}", "--", "{prompt}"),
           "answerer": ("-p", "--output-format", "json", "--tools", "", "--json-schema", "{schema_json}",
                        "--strict-mcp-config", "--setting-sources", "project,local", "--disable-slash-commands",
                        "--no-session-persistence", "?--model={model}", "--", "{prompt}")},
          _claude_reply, default_model="claude-opus-5-5", confines_reads=True, temp_env="CLAUDE_CODE_TMPDIR",
          actions=_claude_actions,
          message=lambda prompt: json.dumps({"type": "user", "message": {"role": "user", "content": prompt}}),
          turn_done=_claude_turn_done),
    Agent("codex", "openai", ("codex",),
          ("/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex",),
          ("login", "status"), lambda report: "chatgpt" in report.lower(),
          "Open the ChatGPT app, or run `codex login`, and sign in with ChatGPT rather than an API key.",
          {"worker": ("exec", "--json", "--ephemeral", "-s", "workspace-write", "?--model={model}", "--", "{prompt}"),
           "task-worker": (*_CODEX_EXEC, *_CODEX_CONFINED, "?--model={model}", "--", "{prompt}"),
           "task-asker": (*_CODEX_EXEC, *_CODEX_CONFINED, "--output-schema", "{schema}", "?--model={model}",
                          "--", "{prompt}"),
           "task-rewriter": (*_CODEX_EXEC, *_CODEX_CONFINED, "?--model={model}", "--", "{prompt}"),
           "task-interviewer": ("app-server", "--stdio", "--strict-config", *_CODEX_CONFINED,
                                '?--config=model="{model}"'),
           "rewriter": ("exec", "--json", "--ephemeral", "-s", "read-only", "?--model={model}", "--", "{prompt}"),
           "asker": ("exec", "--json", "--ephemeral", "-s", "read-only", "--output-schema", "{schema}",
                     "?--model={model}", "--", "{prompt}"),
           "judge": ("exec", "--json", "--ephemeral", "-s", "read-only", "--skip-git-repo-check", "--output-schema",
                     "{schema}", "?--model={model}", "--", "{prompt}"),
           "answerer": (*_CODEX_EXEC, *_CODEX_CONFINED, "-c", "features.shell_tool=false", "-c",
                        "features.unified_exec=false", "--skip-git-repo-check", "--output-schema", "{schema}",
                        "?--model={model}", "--", "{prompt}")},
          _codex_reply, confines_reads=True, actions=_codex_actions, message=lambda prompt: prompt,
          turn_done=_codex_turn_done, session=_CodexSession, slots=_codex_slots, session_version="json-rpc/1"),
)}
