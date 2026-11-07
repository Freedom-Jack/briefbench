# Changelog

Versions of the `brief` skill, newest first. The bench has its own version, in `pyproject.toml`, and no releases yet; if it gets them, its entries will be headed `## bench <version>`.

A skill version is the `metadata.version` in [SKILL.md](skills/brief/SKILL.md). [plugin.json](plugin.json) carries the same number, because Claude Code compares it to offer an update. Each entry also gives the bench's hash of the skill folder (`scripts/package_skill.py` prints it), the identity experiments record. A test checks that the newest entry matches the folder as it is, so a change to `skills/brief/` needs a new version and entry. A release is the git tag `brief--v<version>` and a GitHub release with the reproducible ZIP.

## brief 0.2.0 (2026-11-04)

Bench hash: `584e1717d2b6c840c53706050e42cd4ef9a6e5e0bad632d1e00cb5b2ae1ccbb9`

- A rewrite of the skill. It asks up to three questions, only where the answer would change the brief; leaves methods and solutions to the agent; can return a prompt unchanged; and stops after the brief.
- Adds `disable-model-invocation: true`, so Claude Code runs it only when called. `agents/openai.yaml` keeps Codex's `allow_implicit_invocation: false`.

## brief 0.1.0 (2026-11-03)

Bench hash: `698d6d2bddf83bb832eb69c82423990607708144190d07ee7bb8a70a50f4f456`

- The first version, which asked three fixed questions. It stays in git at commit 32883ab and was never released.
