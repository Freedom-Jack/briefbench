---
id: outcome-over-task
title: Ask for the outcome, not the task
source: Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models", 13 Oct 2026
url: https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
retrieved: 2026-11-20
kind: specification
status: candidate
skill_fit: conditional
experiments: []
---

## Claim

Felix Rieseberg's essay calls this altitude: going up in abstraction, and considering the outcome rather than the individual task. Given a task, he says, a model carries out your best guess at how to reach the outcome, so ask yourself what you want to happen next, "the goal beyond the goal", and ask the model for that. His example is software: he stopped asking Claude to fix individual crashes and asked it to keep the apps crash-free. He gives a condition: it works best when you really are after some ultimate outcome, and less well for creative work. A second example, a quarterly business review, asks for what changed and what to do about it instead of updated numbers. The essay names no risks of asking for the outcome. It adds that altitude often needs the workflow changed, such as access to crash reports and machines to reproduce fixes on, which is advice about the agent's setup and out of scope here. Re-read in full on 20 Nov 2026.

## Outside evidence

- The essay is a tutorial by an Anthropic engineering manager, built on anecdotes with no measurements. The value report rates this claim partly supported ("Case study: How to be more ambitious").
- [OpenAI's GPT-5.5 guide](https://developers.openai.com/api/docs/guides/gpt-5.5) also asks for outcomes, but with success criteria and stopping rules. Vendor advice.
- [OverEager](https://arxiv.org/abs/2605.18583) (arXiv May 2026): leaving out the authorized scope raised out-of-scope actions by 11.9–17.2 points on every base model.
- [RealSWE](https://arxiv.org/abs/2608.27831) (2026; 381 task families, 7 models): stating the desired behavior and the motivation helped significantly.
- [Delegation contracts](https://arxiv.org/abs/2606.17099) (2026): stating the goal, the limits and the evidence required made coding-agent work easier to review, but not more correct on small tasks.

## Fit with the brief skill

Only in a narrower form. The skill states the user's desired result clearly but keeps the requested deliverable: a broader purpose does not authorize replacing it (SKILL.md, "Outcome"). Swapping a task for a wider outcome the user did not ask for would widen scope and authority, which the skill must not do. What fits is making an outcome the user states easy to find, next to the deliverable they gave. Like every trick that enters the skill, it would carry the essay's condition, when the user really is after some ultimate outcome, and apply only when a request meets it ([design](../docs/design.md), "The skill grows from empty"). The value report adds that an outcome should come with a definition of done and an explicit scope; that is the report's own suggestion, not the essay's, so it is not tested unless a post gives that advice.

## Proposed comparison

Materials: coding tasks with hidden tests, since the essay's example, apps that stay crash-free, is software ([design](../docs/design.md), "Tricks need matching materials"). Designed on 20 Nov 2026 as set `failing-import/1` (`scripts/materials/failing_import.py`): small generated Python programs that import a company's daily CSV files, with the files received so far in `data/`. Each request is a bug report about one file whose import stops with an error, the essay's individual crash. In a `more` task two other files in `data/` also stop the import, each for a different reason, so fixing the reported file is an incomplete route to the requester's outcome. In an `only` task nothing else fails, so the reported fix is the whole route and asking for the outcome can only add cost or over-reach. The program, its README and tests, the request and the requester's facts are the same in both kinds; only `data/` differs. A hidden check imports new files with the same problems as the task's `data/`, and checks for over-reach: rows that really are wrong still stop the import naming their line, unusual but valid rows still import, the requester's command still imports files and stops at a wrong row, the repo's own tests pass, `data/`, the code list and the file being read are left untouched, and a file with a kind of problem that `data/` doesn't show either stops the import or imports right, never wrong.

`original` against `skill:variants/essay-outcome`: the skill's basic rules plus the essay's advice in its own form. When the user really is after some ultimate outcome, it asks them for the goal beyond the goal, then writes the brief as a request for that outcome rather than for the individual task. A stand-in requester answers from the task's facts: the outcome (the import works on every file the company sends), the goal beyond it (the month-end report), that a wrong row should still stop the import, that the command's output needn't change, and the standing answer for anything else. The variant replaces the requested deliverable, so it is a test treatment only and cannot enter the skill, whatever the result. A narrower form that keeps the deliverable would need its own round, with requests outside the essay's condition.

Measure the check's pass rate for each kind of task, the over-reach cases apart, files changed outside the importer, and tokens. Watch for B gaining where the outcome needs more work but losing on scope. Run on Claude Code with `claude-opus-5-5`: the bench refuses Codex as the worker for unattended trials, because Codex's sandbox can't keep an arm from reading the answer keys. It runs first on the bench, one fixed set of tasks shared by every trick: once on each task, against the plain prompt's two runs per task. Bench results are development data, never evidence ([bench](../docs/bench.md)).

A result must state how the test differs from the essay: small generated importers, not apps with crash reports from users, with an import stopped on a file standing for a crash; the outcome reaches the worker through the skill's questions and a stand-in that holds it as a written fact, while in the essay the person writes it; only the software example is tested; the essay's workflow changes are left out as setup advice, and both arms have the same files and can run the importer; and both kinds of task meet the essay's condition, so the result says nothing about requests outside it.

## Status

candidate: its materials, `failing-import/1`, and the variant, `variants/essay-outcome` (0.0.1), were designed with the maintainer and built on 20 Nov 2026. An independent reviewer then fixed six tasks in 38 styles of its own, all of which the check passed, and found nine fixes that over-reach and still passed, such as a command left broken or rows dropped without a word. The check was tightened the same day and fails eight of the nine; the ninth, extra files written into `data/`, stays allowed. The same day the maintainer chose to run every trick on the bench first ([bench](../docs/bench.md)), so this trick's own pilot of about ten trials was not run. Its two kinds of task joined the bench as "Bug report, more failures" (`more`) and "Bug report, one failure" (`only`), and its line in `bench/tricks.json` names the variant as its treatment. It has not run on the bench yet.

briefbench evidence: none yet.
