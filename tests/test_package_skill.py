"""scripts/package_skill.py: a reproducible zip of the skill, tied to the bench's identity of it. Offline; every
run writes only to a temporary folder."""
import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

import pytest

from briefbench.treatments import folder_sha256

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "package_skill.py"
SKILL = ROOT / "skills" / "brief"
SKIPPED = {".git", "__pycache__", ".DS_Store"}
BENCH = "bench skill hash (matches experiments' sha256 for skill:"
LONG = "a" * 65


def package(tmp_path, *args):
    """Run the script from a temporary folder, so that a stray relative path can only land there."""
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=tmp_path, capture_output=True, text=True,
                          timeout=120)


def printed(result, label):
    """The value on the script's `label...: value` line."""
    return next(line for line in result.stdout.splitlines() if line.startswith(label)).rpartition(": ")[2]


def zip_names(folder):
    """The skill's files as the zip should name them, in its order."""
    files = sorted(PurePosixPath(p.relative_to(folder).as_posix()) for p in folder.rglob("*") if p.is_file())
    return [f"brief/{rel}" for rel in files if not SKIPPED & set(rel.parts)]


def skill_copy(tmp_path, edit=lambda text: text, folder="brief"):
    """A copy of the real skill outside the repo, with SKILL.md passed through edit."""
    copy = tmp_path / "copy" / folder
    shutil.copytree(SKILL, copy, ignore=shutil.ignore_patterns(*SKIPPED))
    skill_md = copy / "SKILL.md"
    skill_md.write_text(edit(skill_md.read_text(encoding="utf-8")), encoding="utf-8")
    return copy


def sub(pattern, replacement):
    """An edit of SKILL.md that must change exactly one place, so that a refusal test can't pass vacuously."""
    def edit(text):
        changed, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
        assert count == 1, pattern
        return changed
    return edit


def pad(lines):
    """An edit that makes SKILL.md exactly `lines` lines long."""
    def edit(text):
        missing = lines - len(text.splitlines())
        assert text.endswith("\n") and missing >= 0
        return text + "".join(f"Filler line {i}.\n" for i in range(missing))
    return edit


def test_the_same_source_gives_the_same_zip(tmp_path):
    first = package(tmp_path, "--out", str(tmp_path / "one"))
    assert first.returncode == 0, first.stderr
    version = printed(first, "version")
    declared = re.search(r'^[ \t]+version:[ \t]*["\']?([^"\'\n]+?)["\']?[ \t]*$', (SKILL / "SKILL.md").read_text(),
                         re.M)
    assert version == declared[1]
    zip_one, zip_two = (tmp_path / out / f"brief-{version}.zip" for out in ("one", "two"))
    built = zip_one.read_bytes()
    assert printed(first, "zip sha256") == hashlib.sha256(built).hexdigest()

    zip_two.parent.mkdir()
    zip_two.write_bytes(b"an older zip of the same name\n")
    second = package(tmp_path, "--out", str(tmp_path / "two"))
    assert second.returncode == 0 and zip_two.read_bytes() == built
    assert "replaced an earlier" in second.stderr               # same version, different bytes: said out loud

    again = package(tmp_path, "--out", str(tmp_path / "one"))
    assert again.returncode == 0 and zip_one.read_bytes() == built and "replaced" not in again.stderr
    assert sorted(p.name for p in zip_one.parent.iterdir()) == [zip_one.name]      # nothing left behind


def test_the_zip_holds_exactly_the_skill_files_with_their_bytes(tmp_path):
    result = package(tmp_path, "--out", str(tmp_path))
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(tmp_path / f"brief-{printed(result, 'version')}.zip") as archive:
        infos = archive.infolist()
        assert [info.filename for info in infos] == zip_names(SKILL)
        for info in infos:
            assert archive.read(info) == (SKILL / info.filename.removeprefix("brief/")).read_bytes()
            assert info.date_time == (1980, 1, 1, 0, 0, 0) and info.external_attr >> 16 == 0o100644
            assert info.compress_type == zipfile.ZIP_STORED
    assert printed(result, "files") == ", ".join(zip_names(SKILL))
    assert printed(result, BENCH) == folder_sha256(SKILL.resolve())


def test_caches_and_git_data_are_left_out_as_the_bench_leaves_them_out(tmp_path):
    copy = skill_copy(tmp_path)
    for junk in (".DS_Store", "agents/.DS_Store", "__pycache__/x.pyc", ".git/HEAD"):
        (copy / junk).parent.mkdir(exist_ok=True)
        (copy / junk).write_bytes(b"junk\n")
    result = package(tmp_path, "--skill", str(copy), "--out", str(tmp_path / "out"))
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(tmp_path / "out" / f"brief-{printed(result, 'version')}.zip") as archive:
        assert archive.namelist() == zip_names(SKILL)
    assert printed(result, BENCH) == folder_sha256(copy.resolve()) == folder_sha256(SKILL.resolve())


@pytest.mark.parametrize("edit, folder, message", [
    (sub(r"^name: brief$", "name: Brief"), "brief", "name 'Brief' must be"),
    (sub(r"^name: brief$", "name: other"), "brief", "must match the skill's folder name"),
    (sub(r"^name: brief$", f"name: {LONG}"), LONG, "at most 64"),
    (sub(r"^description:.*\n", ""), "brief", "description is missing"),
    (sub(r"^description:.*$", "description: " + "x" * 1025), "brief", "1025 characters"),
    (sub(r"^[ \t]+version:.*\n", ""), "brief", "metadata.version is missing"),
    (sub(r"^metadata:$", "tags: x\nmetadata:"), "brief", "unknown front-matter field tags"),
    (sub(r"\A---\n", ""), "brief", "must start with a '---' line"),
    (pad(151), "brief", "151 lines"),
], ids=["bad name", "name is not the folder", "long name", "no description", "long description", "no version",
        "unknown field", "no front matter", "151 lines"])
def test_a_bad_skill_is_refused(tmp_path, edit, folder, message):
    copy = skill_copy(tmp_path, edit, folder)
    result = package(tmp_path, "--skill", str(copy), "--out", str(tmp_path / "out"))
    assert result.returncode == 1 and message in result.stderr, result.stderr
    assert not (tmp_path / "out").exists()


def test_a_skill_at_the_limits_is_packaged(tmp_path):
    name = "a-" * 31 + "bc"                                     # 64 characters

    def edit(text):
        text = sub(r"^name: brief$", f"name: {name}")(text)
        return pad(150)(sub(r"^description:.*$", "description: " + "x" * 1024)(text))

    result = package(tmp_path, "--skill", str(skill_copy(tmp_path, edit, name)), "--out", str(tmp_path / "out"))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out" / f"{name}-{printed(result, 'version')}.zip").is_file()


@pytest.mark.parametrize("kind", ["hidden", "symlink"])
def test_files_that_should_not_ship_are_refused(tmp_path, kind):
    copy = skill_copy(tmp_path)
    if kind == "hidden":
        (copy / "agents" / ".env").write_text("X=1\n")
    else:
        (tmp_path / "elsewhere.md").write_text("not part of the skill\n")
        (copy / "notes.md").symlink_to(tmp_path / "elsewhere.md")
    result = package(tmp_path, "--skill", str(copy), "--out", str(tmp_path / "out"))
    assert result.returncode == 1 and f"is {'hidden' if kind == 'hidden' else 'a symlink'}" in result.stderr
    assert not (tmp_path / "out").exists()


def test_the_zip_never_goes_into_the_skill_folder(tmp_path):
    copy = skill_copy(tmp_path)
    before = folder_sha256(copy)
    result = package(tmp_path, "--skill", str(copy), "--out", str(copy / "dist"))
    assert result.returncode == 1 and "inside the skill folder" in result.stderr
    assert folder_sha256(copy) == before and not (copy / "dist").exists()


def test_a_folder_without_skill_md_is_refused(tmp_path):
    result = package(tmp_path, "--skill", str(tmp_path), "--out", str(tmp_path / "out"))
    assert result.returncode == 1 and "no SKILL.md" in result.stderr


@pytest.mark.parametrize("tamper", [None, "extra member", "changed bytes"])
def test_the_read_back_check_refuses_a_zip_unlike_the_source(tmp_path, monkeypatch, tamper):
    # In process: the command line can't be made to build a bad zip. No bytecode is cached next to the script.
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("package_skill", SCRIPT)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    folder = SKILL.resolve()
    files = script.members(folder)
    sources = {rel: (folder / rel).read_bytes() for rel in files}
    if tamper == "changed bytes":
        sources[files[0]] += b"tampered\n"
    target = tmp_path / "brief.zip"
    script.build(target, "brief", sources)
    if tamper == "extra member":
        with zipfile.ZipFile(target, "a") as archive:
            archive.writestr("brief/extra.md", "not in the skill\n")
    if tamper is None:
        script.verify(target, "brief", folder, files, folder_sha256(folder))
    else:
        with pytest.raises(script.Refused):
            script.verify(target, "brief", folder, files, folder_sha256(folder))
