<!--
Pull requests are public: no private prompts, outputs, keys or personal data.
For a new experiment, task pack, adapter or substantial skill change, link the issue where it was agreed.
AI-assisted work is welcome. You are accountable for it, so explain it and check it.
-->

## Problem and change

<!-- The problem or decision this addresses, and the change you made. -->

## Issue and evidence

<!-- The issue this closes or relates to, and any evidence behind the change. -->

## Validation

<!-- What you ran, and what you checked by hand. -->

## Compatibility

<!-- Effects on CLI behavior, exit codes, or the log and record formats (docs/data-formats.md). Formats gain fields; they never lose or change them. -->

## Rights and attribution

<!-- Confirm you have the right to submit everything included. Name any third-party material, its source and its license. -->

## Release and evidence

<!-- Does a skill release, a task version, or how existing results are read need to change? -->

## Checklist

- [ ] Offline tests pass on Python 3.11 (`uv run pytest`) and 3.14 (`uv run --isolated --python 3.14 pytest`)
- [ ] If `skills/brief/` changed: `metadata.version` is bumped, `plugin.json` carries the same version, `CHANGELOG.md` has an entry with the new bench hash, and this pull request says it starts a new experiment
- [ ] No private prompts, outputs, keys or personal data
- [ ] Docs updated if behavior changed
