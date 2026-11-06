---
id: caps-emphasis
title: Emphasize rules with capitals and CRITICAL
source: common advice with no single author, as recorded in the briefbench research report "The value of prompting techniques with frontier models", 4 Nov 2026, section "Judging posts like this"
url: https://github.com/Freedom-Jack/briefbench/blob/main/docs/research/value-of-prompting/report.md
retrieved: 2026-11-04
kind: wording
status: deferred
skill_fit: no
experiments: []
---

## Claim

Common advice says to mark important rules with capitals and words such as CRITICAL and MUST, so the model follows them. The value report notes that emphatic tool rules were used against undertriggering on earlier Claude models ([snapshot](../docs/research/value-of-prompting/report.md)).

## Outside evidence

- Vendor advice only. The value report found no controlled study of emphasis on any model, and the benchmarks report found no rigorous one.
- Anthropic says Opus 4.5 and 4.6 might now overtrigger on such rules, and suggests plain wording that says when to use a tool ([best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).
- OpenAI's [GPT-4.1 guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide) calls capitals generally not necessary.
- The advice flipped between consecutive versions of one model family, which the report reads as a sign that such effects belong to model versions, not vendor families.

## Fit with the brief skill

No. Emphasis adds pressure, not information, and the skill avoids invented urgency and instructions that could be appended to any task (SKILL.md). It adds no emphasis of its own, and has no rule about emphasis already in the user's prompt.

## Proposed comparison

The released skill as `skill:<folder>` against `skill:variants/brief-emphasis`, which writes the user's requirements in emphatic form; a snippet cannot do this, since it only adds text. Measure the check's pass rate, the blind pick, tokens, and work beyond the request in the diffs, where overtriggering would show.

## Status

deferred: docs/design.md tests single techniques only after the whole brief wins against the original, and the report rates this one a liability on frontier models.

briefbench evidence: none yet.
