---
id: controlled-language
title: Make the model write in controlled language
source: Charlie Hills' AI OS, LinkedIn post on the ASD-STE100 prompting trick, about 23 Oct 2026 (shown as two weeks old on 6 Nov 2026)
url: https://www.linkedin.com/posts/charlie-hills_theres-a-weird-prompting-trick-called-asd-ste100-activity-7519399737607876609-HoPa
retrieved: 2026-11-06
kind: wording
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

A viral post says that pasting five rules from ASD-STE100, the controlled English of aircraft manuals, into Claude's custom instructions gives clearer answers. The rules: active voice, no sentence over 20 words, one idea per sentence, the same word for the same thing, and no idioms or jargon.

## Outside evidence

- None found. The post gives no measurement, and it promotes a paid tool set.
- No study of controlled-language instructions for current models turned up in a search on 6 Nov 2026. The value report's general finding is that phrasing tricks rarely change accuracy on current models ([snapshot](../docs/research/value-of-prompting/report.md), "Phrasing techniques").

## Fit with the brief skill

Only in a narrower form. Asking the agent to answer in controlled language is an instruction that could be appended to any task, which the skill avoids (SKILL.md). The skill could follow the rules in its own sentences, while keeping the user's names, numbers and quoted text exactly. That would be a separate wording candidate.

## Proposed comparison

Materials: the claim is about clarity, so open-ended tasks with a written deliverable, judged by your blind pick ([design](../docs/design.md), "Tricks need matching materials"). Analysis tasks with a planted answer can serve as a side check that clarity doesn't cost correctness.

`original` against `snippet:snippets/controlled-language.md`, which holds the five rules as the post gives them. Report average sentence length per arm as a side measure.

## Status

deferred: the claim needs your blind picks. The unattended tests come first.

briefbench evidence: none yet.
