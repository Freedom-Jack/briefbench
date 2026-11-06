# Research

Background research for briefbench: what already exists, and what the evidence says about prompting. These reports inform the design but don't change it. Decisions live in [design.md](../design.md); [design-review.md](../design-review.md) shows where each research recommendation landed, and [design-research.md](../design-research.md) adds later primary-source checks.

## Reports

| Date | Topic | Question | Working copy (private) | Snapshot |
| --- | --- | --- | --- | --- |
| 2026-10-28 | Prompt optimizer landscape | Does any tool already rewrite everyday prompts, learn from your results and prove the gain on your own tasks? | [Claude Doc](https://claude.ai/artifact/2HydZRFVYEeriMbFGUi1aH) | [report](prompt-optimizer-landscape/report.md) |
| 2026-11-04 | Prompting technique benchmarks | Does any benchmark rank prompting techniques the way leaderboards rank models, and which gaps are left for briefbench? | [Claude Doc](https://claude.ai/artifact/Lry4fZNsVyH4hzV3wAuFbe) | [report](prompting-technique-benchmarks/report.md), [research record](prompting-technique-benchmarks/research-record.md) |
| 2026-11-04 | Value of prompting techniques | Do prompting techniques still pay on frontier models, both general ones and ones tailored to a model family such as Claude or GPT, and is a technique bench worth building? | [Claude Doc](https://claude.ai/artifact/8QsRiwWqCoi3kT6dH1FJF9) | [report](value-of-prompting/report.md) |

## Bottom lines

- **Prompt optimizer landscape.** No tool does all three parts of the idea. Of 23 tools reviewed, the closest scores 6 of 8 and has no evidence that it works. GEPA is the only tool whose gains were confirmed outside its authors.
- **Prompting technique benchmarks.** No maintained benchmark ranks prompting techniques. Most parts of briefbench have a precedent, but nothing combines them, and four gaps look open. At personal scale, only large effects will be detectable.
- **Value of prompting techniques.** Phrasing tricks have lost most of their value on frontier models. Specification keeps paying, and the harness moves agent results most. Model-specific prompting belongs to model versions and expires within one or two releases. So the bench should test the brief against the original prompt and re-run when the model changes, rather than rank techniques. The report also tests Felix Rieseberg's essay "How to be more ambitious" and five 2026 posts by well-known practitioners, claim by claim.

## How this folder works

- **One folder per topic.** `report.md` is a snapshot of the topic's Claude Doc. The PNG files are images of the doc's interactive charts.
- **The snapshot here is the public copy.** Each report was written as a Claude Doc, the maintainer's private working copy, and exported here. To correct a report, open a pull request against its snapshot; the maintainer carries the change into the working copy, so the next refresh keeps it.
- **Refreshing a snapshot.** Export each doc tab as Markdown with the Claude Docs connector. Add the snapshot note under the date line, and replace each `[embedded content: …]` chart placeholder with a current image of the chart.
- **The raw research runs are kept privately.** Each run's own outputs (`raw/` folders, git-ignored) are bulky and quote their sources at length; they are not needed to check a report, whose sources are all linked. A local note, `LOCAL.md`, also git-ignored, lists them and the sessions they came from.
- **Adding a topic.** Create a folder with a short kebab-case name, add the snapshot, then add the topic to the tables in this file.
