"""Package the brief skill as a reproducible zip, tied to the bench's identity of the skill.

    uv run python scripts/package_skill.py [--out DIR]

First it checks the skill. SKILL.md's front matter must follow the Agent Skills rules: a lower-case name that
matches the folder, and a description of at most 1024 characters. It must have a metadata.version, and be at
most 150 lines long. The folder must hold no symlinks or hidden files, which could ship something by accident.

Then it writes <out>/<name>-<version>.zip (default out: dist/ in the repo). The zip holds one top-level <name>/
folder with every file of the skill folder except .git, __pycache__ and .DS_Store: the files the bench hashes.
Members are in sorted order and stored uncompressed, with a fixed time (1980-01-01 00:00:00) and mode (0644), so
the same source gives the same bytes. The source files' own modes are not kept. Before the zip replaces an
earlier one of the same name, it is read back and checked against the source, and unzipped to check its hash.

It prints the version, the files, the zip, the zip's sha256 and the bench's hash of the skill folder. That hash
is the sha256 an experiment records for skill:<folder>, and for `brief` when the installed copy holds the same
files. Nothing is installed, and nothing goes over the network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

try:
    from briefbench.treatments import folder_sha256
except ImportError as error:
    sys.exit(f"package_skill: can't import the bench's folder hash ({error}). "
             "Run this as `uv run python scripts/package_skill.py`.")

ROOT = Path(__file__).resolve().parent.parent
SKIPPED = {".git", "__pycache__", ".DS_Store"}          # what the bench's folder hash leaves out
FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools",    # Agent Skills
          "disable-model-invocation"}                   # the project's one extra field (AGENTS.md)
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")          # lower-case letters and digits, single inner hyphens
VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]*")    # fits in a file name
LINE = re.compile(r"(?P<indent> *)(?P<key>[A-Za-z0-9_.-]+):(?:[ \t]+(?P<value>.*?))?[ \t]*")
MAX_LINES, MAX_NAME, MAX_DESCRIPTION, MAX_COMPATIBILITY = 150, 64, 1024, 500
STAMP = (1980, 1, 1, 0, 0, 0)                           # the earliest time a zip can hold
MODE = 0o100644 << 16                                   # a regular file, rw-r--r--, as a zip made on Unix holds it
UNIX = 3                                                # the zip "made by" system that gives MODE its meaning


class Refused(Exception):
    """A check failed. Each argument is one problem, worded for the person running the script."""


def scalar(raw: str | None, where: str) -> str | None:
    """A one-line YAML value as text, or None when it is empty."""
    raw = raw or ""
    if raw[:1] in ("'", '"'):
        found = re.fullmatch(r"""(?:'((?:[^']|'')*)'|"((?:[^"\\]|\\.)*)")(?:[ \t]+#.*)?""", raw)
        if not found:
            raise Refused(f"{where}: close the quoted value on the same line")
        if found[1] is not None:
            return found[1].replace("''", "'")
        try:
            return json.loads(f'"{found[2]}"', strict=False)        # JSON's escapes are a subset of YAML's
        except ValueError:
            raise Refused(f"{where}: in double quotes, use only the escapes \\\" \\\\ \\/ \\b \\f \\n \\r \\t "
                          "and \\uXXXX") from None
    value = re.split(r"[ \t]#", raw, maxsplit=1)[0].rstrip()         # " #" starts a comment
    if not value or value[0] == "#":
        return None
    if value[0] in "[]{},&*!|>%@`" or value[:2] in ("- ", "? ") or ": " in value or value.endswith(":"):
        raise Refused(f"{where}: write this value on one line, in quotes if it holds ': ' or starts with a symbol")
    return value


def front_matter(text: str) -> dict:
    """SKILL.md's front matter as {key: text}, with one level of nesting as {key: {key: text}}.

    It reads only one-line plain or quoted values. Anything else is refused, rather than guessing what a host's
    YAML parser would make of it."""
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        raise Refused("SKILL.md must start with a '---' line that opens its front matter")
    end = next((i for i, line in enumerate(lines[1:], 1) if line.rstrip() == "---"), None)
    if end is None:
        raise Refused("SKILL.md's front matter has no closing '---' line")
    fields: dict = {}
    parent = depth = None
    for number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        where = f"SKILL.md line {number}"
        found = LINE.fullmatch(line)
        if not found:
            raise Refused(f"{where}: write each field as one 'key: value' line, indented with spaces if nested")
        key, value = found["key"], scalar(found["value"], where)
        if not found["indent"]:                     # a top-level field; a bare "key:" opens a nested map
            into, parent, depth = fields, (key if value is None else None), None
            value = {} if value is None else value
        elif parent and value is not None and depth in (None, len(found["indent"])):
            into, depth = fields[parent], len(found["indent"])
        else:
            raise Refused(f"{where}: only one level of nested keys is read, each with a value on its own line")
        if key in into:
            raise Refused(f"{where}: {key} is set twice")
        into[key] = value
    return fields


def check(folder: Path, text: str) -> tuple[str, str]:
    """The skill's name and version. Refused lists every problem found."""
    problems = []
    if len(text.splitlines()) > MAX_LINES:
        problems.append(f"SKILL.md is {len(text.splitlines())} lines; the project's limit is {MAX_LINES}")
    try:
        fields = front_matter(text)
    except Refused as error:
        raise Refused(*problems, *error.args) from None
    unknown = sorted(set(fields) - FIELDS)
    if unknown:
        problems.append(f"unknown front-matter field {', '.join(unknown)}: the skill uses only the Agent Skills "
                        "fields and disable-model-invocation (AGENTS.md). To allow another, add it to FIELDS here")
    name, description = fields.get("name"), fields.get("description")
    if not isinstance(name, str):
        problems.append("name is missing")
    elif len(name) > MAX_NAME or not NAME.fullmatch(name):
        problems.append(f"name {name!r} must be at most {MAX_NAME} lower-case letters, digits and single hyphens, "
                        "with no hyphen at either end")
    elif name != folder.name:
        problems.append(f"name {name!r} must match the skill's folder name, {folder.name!r}")
    if not isinstance(description, str) or not description.strip():
        problems.append("description is missing or empty")
    elif len(description) > MAX_DESCRIPTION:
        problems.append(f"description is {len(description)} characters; the limit is {MAX_DESCRIPTION}")
    compatibility = fields.get("compatibility")
    if isinstance(compatibility, str) and len(compatibility) > MAX_COMPATIBILITY:
        problems.append(f"compatibility is {len(compatibility)} characters; the limit is {MAX_COMPATIBILITY}")
    metadata = fields.get("metadata")
    version = metadata.get("version") if isinstance(metadata, dict) else None
    if not version:
        problems.append("metadata.version is missing")
    elif not VERSION.fullmatch(version):
        problems.append(f"metadata.version {version!r} must be letters, digits and . + _ - only, to name the zip")
    if problems:
        raise Refused(*problems)
    return name, version


def members(folder: Path) -> list[PurePosixPath]:
    """The files to package, relative to the folder, in the zip's order. By design, the files the bench hashes."""
    found, problems = [], []
    for path in sorted(folder.rglob("*")):
        rel = PurePosixPath(path.relative_to(folder).as_posix())
        if SKIPPED & set(rel.parts):
            continue
        if path.is_symlink():
            problems.append(f"{rel} is a symlink; replace it with the file itself")
        elif rel.name.startswith("."):
            problems.append(f"{rel} is hidden; remove it, or it ships in the zip and counts in the bench hash")
        elif path.is_file():
            found.append(rel)
    if problems:
        raise Refused(*problems)
    return sorted(found)


def build(target: Path, name: str, sources: dict[PurePosixPath, bytes]) -> None:
    """Write the zip so that its bytes depend on the source alone."""
    with zipfile.ZipFile(target, "w") as archive:
        for rel in sorted(sources):
            info = zipfile.ZipInfo(f"{name}/{rel}", date_time=STAMP)
            info.compress_type, info.create_system, info.external_attr = zipfile.ZIP_STORED, UNIX, MODE
            archive.writestr(info, sources[rel])


def verify(target: Path, name: str, folder: Path, files: list[PurePosixPath], bench: str) -> None:
    """Read the zip back. It must hold exactly the skill's files, in order, each with the source's bytes and the
    fixed time and mode. Unzipped, it must have the bench hash of the source folder."""
    with zipfile.ZipFile(target) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != [f"{name}/{rel}" for rel in files]:
            raise Refused(f"the zip holds {', '.join(names)}, which are not exactly the skill's files")
        for info, rel in zip(infos, files):
            if archive.read(info) != (folder / rel).read_bytes():       # read() also checks the CRC
                raise Refused(f"{info.filename} in the zip differs from {rel} in the skill folder")
            if (info.date_time, info.external_attr, info.create_system, info.compress_type) != \
                    (STAMP, MODE, UNIX, zipfile.ZIP_STORED):
                raise Refused(f"{info.filename} lacks the fixed time, mode or storage that make the zip reproducible")
        with tempfile.TemporaryDirectory(prefix=f".{name}-check-", dir=target.parent) as scratch:
            archive.extractall(scratch)
            if folder_sha256(Path(scratch, name).resolve()) != bench:
                raise Refused("unzipped, the zip does not have the bench hash of the skill folder")


def shown(path: Path) -> str:
    """A path as the user would type it: relative to the current folder when it is inside it."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="package_skill", allow_abbrev=False,
                                     description="Package the brief skill as a reproducible zip.")
    parser.add_argument("--out", type=Path, default=ROOT / "dist",
                        help="folder for the zip (default: the repo's dist/)")
    parser.add_argument("--skill", type=Path, default=ROOT / "skills" / "brief",
                        help="skill folder to package (default: the repo's skills/brief)")
    args = parser.parse_args(argv)
    folder, out = args.skill.expanduser().resolve(), args.out.expanduser().resolve()
    try:
        if not (folder / "SKILL.md").is_file():
            raise Refused(f"there is no SKILL.md in {shown(folder)}")
        if out.is_relative_to(folder):
            raise Refused(f"--out {shown(out)} is inside the skill folder, so the zip would ship in the next zip")
        files = members(folder)
        sources = {rel: (folder / rel).read_bytes() for rel in files}
        try:
            text = sources[PurePosixPath("SKILL.md")].decode("utf-8")
        except UnicodeDecodeError:
            raise Refused("SKILL.md is not valid UTF-8") from None
        name, version = check(folder, text)
        bench = folder_sha256(folder)
        out.mkdir(parents=True, exist_ok=True)
        target = out / f"{name}-{version}.zip"
        part = target.with_name(target.name + ".part")
        try:
            build(part, name, sources)
            verify(part, name, folder, files, bench)
            before = sha256(target) if target.is_file() else None
            os.replace(part, target)
        finally:
            part.unlink(missing_ok=True)
    except Refused as refusal:
        print(f"package_skill: can't package {shown(folder)}:", *(f"  - {p}" for p in refusal.args),
              sep="\n", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"package_skill: {error}", file=sys.stderr)
        return 1
    digest = sha256(target)
    if before and before != digest:
        print(f"package_skill: note: replaced an earlier {target.name} that had different bytes. If that one was "
              "released, bump metadata.version: one version should name one set of files.", file=sys.stderr)
    print(f"version: {version}")
    print(f"files: {', '.join(f'{name}/{rel}' for rel in files)}")
    print(f"zip: {shown(target)}")
    print(f"zip sha256: {digest}")
    print(f"bench skill hash (matches experiments' sha256 for skill:{shown(folder)}): {bench}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
