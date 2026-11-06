# Design history

How the design got to [design.md](design.md). Each earlier version is kept in git; this page says where, and what changed. None of the earlier documents are implementation instructions.

| Date | Version | What it decided | Where it lives |
| --- | --- | --- | --- |
| 2026-10-28 | First plan | A CLI that rewrites a prompt through vendor APIs, keeps it word for word and appends one section per technique, then A/B tests and adapts a playbook in later stages. Python, data under `~/.briefbench/` | `docs/design.md` at commit 9be1d26 |
| 2026-10-29 | First plan, stage 1 built | `briefbench rewrite`: provider layer, question flow, playbook, log (PR #1) | `main` at commit 5662bcc |
| 2026-11-02 | Redesign proposal | Two separate parts: the `brief` skill as the front end and a small bench of blind paired trials as the back end; a third-vendor judge; a two-step sign test fixed in advance | `docs/redesign.md` at commit 6c0341f |
| 2026-11-03 | Redesign, revised and built (stages 0–3) | Subscriptions only, never paid APIs: the API layer and `rewrite` retired. The skill logs nothing. `init`, `ab`, `clean`, the judge and `score` built and run through Codex | `docs/design.md` at commit b5e2867 |
| 2026-11-03 | A parallel line (uncommitted, main checkout) | The skill written again alongside the API CLI, with a rule to keep that CLI; a ten-case synthetic forward check | Not in git; superseded |
| 2026-11-04 | Skill 0.2.0 | Your rewrite of the skill (the parallel line's text) replaces the first, and runs only when called | Commit 52cbd05 |
| 2026-11-04 | Research | Technique benchmarks, and the value of prompting techniques, with case studies of the ambition essay and five practitioners' posts | [research/](research/README.md) |
| 2026-11-04 | Public-project design (uncommitted, main checkout) | The project goes public; claim cards, scoped findings, fidelity, a fixed-sample protocol, an evidence-record backend, a manual-first plan. Written without knowing the bench was built | Its build plan, protocol, records, community plan and research addendum were brought into this branch on 2026-11-05 and revised; its design text is superseded by design.md |
| 2026-11-05 | Reconciled design | The built bench is the base; the public-project direction is adopted; the bench gains the skill's own questions, `clarified`, a hidden evaluation, tie kinds, a fidelity review, failed-trial logging, CLI versions per trial, the `fixed:N` rule and `score --json` | [design.md](design.md), with the reasons in [design-review.md](design-review.md) |

To read an earlier version, for example the built redesign's design: `git show b5e2867:docs/design.md`.
