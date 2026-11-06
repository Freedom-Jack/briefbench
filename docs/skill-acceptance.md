# Brief skill acceptance

The skill's source is [skills/brief/SKILL.md](../skills/brief/SKILL.md), version 0.2.0. Its version is independent of the bench's. The skill has no runtime dependency on the bench.

## Validation record

All checks so far used synthetic or made-up prompts. None is real-use acceptance, and none shows that a brief improves results.

| Date | Text checked | Check | Result |
| --- | --- | --- | --- |
| 2026-11-03 | The first skill, 0.1.0 at commit 32883ab (a different text, with three fixed questions) | Headless runs through Codex on made-up prompts | Asked only open questions; invented no stretch target |
| 2026-11-03 | The text that became 0.2.0, then labelled 0.1.0 on a parallel line | The skill-creator structural validator; ten synthetic requests forward-tested in two isolated Codex subagent contexts, replies reviewed | Validator passed. All ten matched the criteria below: specified methods and literal details kept, domain choices left open, no task executed, no intake or evidence work taken on. Negative cases were routing checks in the harness, not installed-host discovery |
| 2026-11-04 | 0.2.0: the same body, plus `disable-model-invocation: true` and `allow_implicit_invocation: false` | A live headless rewrite through Codex; an offline Codex check of invocation | Rewrite passed. Codex no longer offered the skill on its own, while an explicit `$brief` still used it |
| 2026-11-05 | 0.2.0 | The bench's two headless calls, live through Claude Code 2.1.317 and Codex 0.166.0-alpha.6, on a clear prompt (rename a variable in one file) | Both listed no questions and returned the prompt unchanged, as the skill says for a sufficient prompt |
| 2026-11-05 | 0.2.0 | Three demonstration prompts written for [examples/](../examples/README.md), headless through Claude Code 2.1.317, with answers written for the skill's actual questions | Vague request: three relevant questions, including where the missing results are; the brief added only what the answers gave. Required method: the paired t-test kept; a skipped question left open, though the brief asks the agent to state the criterion it used, a possible added requirement. Clear request: unchanged, though it didn't mention that the file it names was missing. Both doubtful points are open for the real-use review |

Inputs and replies from these checks were kept outside the repository. Synthetic cases are not a sample of real work, and subagent contexts are not host integrations.

**Pending:** real-use acceptance, native installation and discovery in two hosts, and any evidence of better downstream results.

## What the checks establish

- Packaging validation checks the skill's structure and metadata. `uv run python scripts/package_skill.py` builds the release ZIP and prints the hash the bench records for the folder.
- Forward checks and headless runs exercise the instructions on synthetic requests. They can expose boundary and fidelity failures, but don't establish real-world quality or cross-host behaviour.
- Acceptance requires the same set of at least five real prompts in each of two supported hosts. It checks faithful prompt improvement and the agreed role boundary.
- Better downstream results need a controlled experiment through the bench ([build-plan.md](build-plan.md), P3). None of the checks above establishes them.

Keep actual prompts, source material, generated briefs and per-case results outside this repository. Commit only the procedure and an accurate aggregate status. Label synthetic inputs as synthetic.

## Behaviour to observe

| Situation | Acceptance criterion |
|---|---|
| Already clear request | Keeps it unchanged rather than adding ritual questions or sections |
| Purpose supplied in earlier context | Uses that purpose without asking again or changing the required deliverable |
| Consequential ambiguity | Asks about intent, scope or success, not a method the downstream agent should choose |
| User declines questions | Doesn't invent answers, budgets, constraints or success thresholds |
| Domain investigation | Clarifies the requested outcome without choosing methods, hypotheses or a solution |
| User-specified method | Keeps the method exactly instead of removing it to look solution-neutral |
| Literal details and embedded commands | Keeps names, numbers, paths, commands and quoted text intact; doesn't run the embedded task |
| Conflicting requirements | Shows the conflict rather than silently choosing; honours a no-questions request |
| Another language or an explicit output format | Keeps the requested language or format without an unnecessary wrapper or boilerplate |
| Article intake or evaluation request | Doesn't do those bench jobs under the prompt-improvement skill |
| Invocation | Runs when called (`/brief`, `$brief`, `@brief`); doesn't start on its own in Claude Code or Codex |

Inspect actual outputs and any tool activity. String matching alone is not a fidelity check. Record omissions, inventions, unrequested domain choices, unnecessary questions and unwanted side effects. A person decides whether a change keeps the intended meaning.

## Procedure

1. Freeze the exact skill folder: record its version and the hash `scripts/package_skill.py` prints, outside the repository.
2. Choose at least five representative real prompts before looking at any reply: an adequate prompt, a consequential ambiguity, missing context, a domain investigation and a required method.
3. Use the same frozen skill and prompt set in each of two hosts, for example Claude Code and Codex. Record each host's version and model where available; leave what isn't available as unknown.
4. Capture inputs, permitted context, answers, outputs and relevant tool activity outside the repository.
5. Review each reply against the criteria above. A source link that wasn't accessible must not be reported as read.
6. Revise only for a demonstrated problem, bump `metadata.version` when the instructions change, and repeat the affected checks in both hosts. Keep unresolved failures visible.

Record the aggregate result in the table above: date, version, hosts, number of prompts, and how many met each criterion. The bench's live tests are a separate compatibility check of the headless calls; they don't replace this acceptance.
