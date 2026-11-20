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
| 2026-11-05 | Reconciled design | The built bench is the base; the public-project direction is adopted; the bench gains the skill's own questions, `clarified`, a hidden evaluation, tie kinds, a fidelity review, failed-trial logging, CLI versions per trial, the `fixed:N` rule and `score --json` | `docs/design.md` at commit 49624b6, with the reasons in [design-review.md](design-review.md) |
| 2026-11-06 | Matching materials, recent posts, growing from empty | Each trick on materials that fit it; only recent posts; the skill rebuilt from empty, one tested change at a time, with 0.2.0 as the reference and a source of candidates; unattended trials scored by a hidden check | `docs/design.md` at commit 2cfa40b |
| 2026-11-09 | The method for public results | Seven steps for every public result, and a second test before a trick is marked better | `docs/design.md` at commit c893ab2, the last version before 2026-11-18 |
| 2026-11-18 | Only prompting advice people have posted | Only posted prompting advice is tested or enters the skill; advice about the agent's setup and the project's own ideas are out; seven cards removed; 0.2.0 no longer a source of candidates; rounds 1 and 2 recorded as tests of the skill's own question section; each trick tested on the kind of work its source is about | `docs/design.md` at commit ecf067a, the last version before 2026-11-20 |
| 2026-11-20 | Only advice people have posted, widened to settings | Posted advice about which model, effort level or multi-agent mode to run a task with is tested too, and can enter the skill only as a note after the brief, in terms that work in any host; seven settings cards, all deferred; a research report on settings advice | [design.md](design.md) |

To read an earlier version, for example the built redesign's design: `git show b5e2867:docs/design.md`.
