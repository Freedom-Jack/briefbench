import ast
import importlib.metadata
import re
import tomllib
from pathlib import Path

import briefbench

SRC = Path(briefbench.__file__).parent
ROOT = Path(__file__).resolve().parent.parent
# Letter-only lookarounds, not \b: "_" is a word character, so \bxai\b misses XAI_API_KEY
VENDOR = re.compile(r"anthropic|claude|gemini|gemma|google|gpt-|o[1-9]-(?:mini|pro)|deepseek|mistral|mixtral|"
                    r"codestral|llama|qwen|ollama|lm.?studio|groq|grok|(?<![a-z])xai(?![a-z])|"
                    r"(?<![a-z])x\.ai(?![a-z])|openrouter|openai(?!_compat|-compatible|compat)|localhost:\d", re.I)
CORE = ("errors", "redact", "provider", "questions", "playbook", "rewrite", "report", "log")
MODULES = {p.stem for p in SRC.glob("*.py")} - {"__init__"}


def local_imports(path: Path) -> set[str]:
    """The modules of this package that a file imports, by short name."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0:                  # absolute: only briefbench's own modules count
                if module != "briefbench" and not module.startswith("briefbench."):
                    continue
                module = module.partition(".")[2]
            first = module.split(".")[0]         # "" for "from . import x": then x is the module
            found.update([first] if first else [a.name for a in node.names])
        elif isinstance(node, ast.Import):
            found.update(a.name.split(".")[1] for a in node.names if a.name.startswith("briefbench."))
    return found & MODULES


def test_core_is_vendor_neutral():
    for path in SRC.glob("*.py"):
        if path.name == "presets.py":
            continue
        found = VENDOR.findall(path.read_text())
        assert not found, (path.name, found)


def test_vendor_pattern_catches_names_inside_identifiers():
    for text in ("XAI_API_KEY", "api.x.ai", "gemma3:12b", "llama3.1", "qwen2.5", "o4-mini", "OPENAI_API_KEY"):
        assert VENDOR.search(text), text
    for text in ("relaxation", "maxai", "openai_compat", "OpenAI-compatible"):
        assert not VENDOR.search(text), text


def test_import_direction():
    for path in SRC.glob("*.py"):
        imported = local_imports(path)
        if path.stem in CORE:
            assert not imported & {"presets", "openai_compat", "selection", "cli"}, path.name
        if path.stem != "selection":
            assert "presets" not in imported, path.name
    assert local_imports(SRC / "openai_compat.py") <= {"errors", "provider", "redact"}
    assert not local_imports(SRC / "cli.py") & {"presets", "openai_compat"}


def test_tls_never_disabled_and_input_never_called():
    text = "".join(p.read_text() for p in SRC.glob("*.py"))
    for bad in ("CERT_NONE", "check_hostname = False", "_create_unverified_context", "verify_mode ="):
        assert bad not in text
    for path in SRC.glob("*.py"):
        calls = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "input"]
        assert not calls, path.name


def test_single_runtime_dependency():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["dependencies"] == ["truststore>=0.10"]


def test_version_matches_metadata():
    assert briefbench.__version__ == importlib.metadata.version("briefbench")
