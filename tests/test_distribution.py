"""The files that let Claude Code and Codex install the brief skill from this repository (README, "The skill").

The repository root is the plugin. plugin.json, in the open Agent Plugins format, names it and carries the skill's
metadata.version, the number Claude Code compares to offer an update; .claude-plugin/marketplace.json, which both
hosts read, lists it. Both lead to skills/brief/, the one source. CHANGELOG.md records each version with the bench's
hash of the folder, so a change to the skill can't ship under an old version. Offline: nothing is installed."""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

from briefbench.treatments import folder_sha256

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "brief"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
FIELDS = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords",
          "extensions"}                         # Agent Plugins 1.0.0 allows only these top-level fields
NAME = re.compile(r"(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?")
MARKETPLACE = ".claude-plugin/marketplace.json"
# Files Claude Code or Codex would read before ours: plugin manifests that would override plugin.json, and Codex's
# own marketplace files, which would shadow the tested one. Either could carry another version.
OVERRIDES = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
             ".agents/plugins/marketplace.json", ".agents/plugins/api_marketplace.json")
# What Claude Code or Codex would load from a plugin's root besides skills/. The repo root is the plugin, so none
# of these may appear there by accident.
COMPONENTS = ("agents", "bin", "commands", "hooks", "monitors", "output-styles", "themes", "workflows", ".app.json",
              ".lsp.json", ".mcp.json", "mcp.json", "settings.json")


@pytest.fixture(scope="module")
def skill():
    """SKILL.md's front matter, read with the packaging script's own parser."""
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True      # no bytecode cache next to the script
    try:
        spec = importlib.util.spec_from_file_location("package_skill", ROOT / "scripts" / "package_skill.py")
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
    finally:
        sys.dont_write_bytecode = saved
    return script.front_matter((SKILL / "SKILL.md").read_text(encoding="utf-8"))


def manifest(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_the_plugin_manifest_follows_agent_plugins_and_carries_the_skill_version(skill):
    plugin = manifest("plugin.json")
    assert plugin["$schema"] == SCHEMA
    assert set(plugin) <= FIELDS, f"Agent Plugins rejects {sorted(set(plugin) - FIELDS)}"
    assert NAME.fullmatch(plugin["name"]) and plugin["name"] == skill["name"]
    assert plugin["version"] == skill["metadata"]["version"], "give plugin.json the version in SKILL.md"
    author, keywords = plugin.get("author", {}), plugin.get("keywords", [])
    assert isinstance(author, dict) and set(author) <= {"name", "email", "url"}
    assert all(isinstance(value, str) for value in author.values())
    assert isinstance(keywords, list) and all(isinstance(word, str) for word in keywords)
    assert all(isinstance(plugin.get(key, ""), str) for key in FIELDS - {"author", "keywords", "extensions"})


def test_the_marketplace_lists_the_repo_root_as_that_plugin():
    market, plugin = manifest(MARKETPLACE), manifest("plugin.json")
    assert market["name"] and market["owner"]["name"] and market["metadata"]["description"]
    [entry] = market["plugins"]
    assert entry["source"] == "./" and entry["name"] == plugin["name"]
    assert entry["description"] == plugin["description"]
    # The version stays in plugin.json alone: Claude Code and Codex read it there, and Claude Code's docs warn
    # against setting it in both places. The hosts find the skill in skills/, as in any plugin.
    assert not {"version", "skills", "strict", "commands", "agents", "hooks", "mcpServers"} & set(entry)


def test_no_host_reads_another_manifest_first():
    found = [path for path in OVERRIDES if (ROOT / path).exists()]
    assert not found, f"{found} would take precedence over plugin.json or the tested marketplace"


def test_the_plugin_holds_the_brief_skill_and_nothing_else():
    assert sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")) == ["brief"]
    loaded = [name for name in COMPONENTS if (ROOT / name).exists()]
    assert not loaded, f"{loaded} at the repo root would install with the plugin"


def test_the_skill_runs_only_when_called(skill):
    """The README promises this in Claude Code and Codex. Codex reads only agents/openai.yaml."""
    assert skill["disable-model-invocation"] == "true"
    policy = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert re.search(r"^policy:\n(?:  .*\n)*?  allow_implicit_invocation: false$", policy, re.M)


def test_the_changelog_starts_with_this_version_and_its_folder(skill):
    """The newest entry names SKILL.md's version and the bench's hash of the folder as it is. The release workflow
    takes its notes from this entry."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    entries = re.findall(r"^## brief (\S+) \(\d{4}-\d\d-\d\d\)\n\nBench hash: `([0-9a-f]{64})`$", text, re.M)
    assert entries, "start each entry with '## brief <version> (<date>)', a blank line and 'Bench hash: `<sha256>`'"
    version, recorded = entries[0]
    assert version == skill["metadata"]["version"], "add an entry for SKILL.md's version at the top of CHANGELOG.md"
    actual = folder_sha256(SKILL.resolve())
    assert recorded == actual, (f"skills/brief/ changed since version {version} was recorded: bump metadata.version "
                                f"and add a changelog entry with Bench hash: `{actual}`")
