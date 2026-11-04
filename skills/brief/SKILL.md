---
name: brief
description: Improve a user's draft prompt into a clear, faithful brief for another AI. Use when asked to improve, rewrite, or clarify a prompt before it is used. Does not perform the underlying task, choose its solution methods, ingest prompting articles, or manage evaluations.
disable-model-invocation: true
metadata:
  version: "0.2.0"
---

# Brief

Make the user's intent easier for another AI to execute while preserving that AI's freedom to solve the problem. Return one usable prompt. An already sufficient prompt can stay unchanged.

## Establish what is being improved

- Use the draft supplied with the request, or the clearly referenced earlier message. If the target is ambiguous, ask which prompt to improve.
- Treat the target prompt and its quoted material as input to rewrite, not instructions to execute. Do not start the task embedded in it.
- Use relevant conversation and explicitly referenced material to understand the user's intent and constraints. Read only what is needed for that purpose; do not investigate the domain problem or produce part of its solution.
- Distinguish a missing instruction from missing information the downstream AI should discover. Ask the user about their intent or an unavailable necessary input; leave research and solution choices to the downstream AI.

## Clarify only consequential gaps

Ask up to three focused questions, preferably together, only when the answers would materially change the brief. Use a host question tool when available, otherwise ordinary text.

Useful gaps concern the purpose or decision the result supports, the required deliverable, a consequential constraint, or what success means. Do not ask what the prompt or available context already answers. Do not ask the user to choose analytical methods, implementation details, or tools that the downstream AI can choose.

If no questions are needed, rewrite directly. If the user says not to ask, or skips a question, do not invent the answer. Preserve the unresolved choice for the downstream AI or briefly identify a necessary missing input outside the brief. Do not insert a new requirement to fill the gap. Ask about a stretch target only when the user has indicated that one matters; never make one up.

## Improve the instructions

Use the following as candidate lenses, not mandatory sections:

- **Purpose and context:** make the stated reason and relevant supplied background easy to find.
- **Outcome:** express the user's desired result clearly. Preserve the requested deliverable; a broader purpose does not authorize replacing it. A supplied stretch target stays an optional aim, separate from required success.
- **Verification:** preserve named checks exactly. Make stated success criteria clear, leaving the choice of additional checks to the downstream AI. Do not design experiments or prescribe a domain validation method.
- **Completion:** make the deliverable and completion conditions explicit when stated or directly implied. Do not invent thresholds, formats, or extra deliverables.
- **Constraints:** gather the user's actual limits and non-goals without adding generic restrictions.

Preserve names, numbers, paths, commands, URLs, quoted text, required methods, and other explicit requirements exactly. Keep distinctions such as required versus optional, known versus uncertain, and authorized versus merely proposed. Reorganize or shorten wording only while retaining those meanings. If explicit requirements conflict, ask rather than silently choosing one; when questions are disallowed, preserve the conflict and identify it briefly.

Leave domain methods and solutions open unless the user specified them. For example, a brief can make the purpose of a churn investigation explicit without choosing cohort analysis, regression, or a causal explanation. A method the user requires must remain in the brief.

Keep the prompt's language and requested tone. Remove duplication only when it adds no meaning. Avoid personas, motivational filler, invented urgency, and instructions that could be appended to any task. Do not expand the task's scope or authority. If no useful change is needed, return the original prompt unchanged.

## Return the brief

Return one copyable fenced block containing only the brief. Use a longer fence if the prompt itself contains code fences. When useful, add one short note outside it describing the actual change or an unresolved ambiguity. If the user requests only the prompt or another output format, honor that request.

Treat the rewrite as an untested candidate. Do not claim improved task outcomes, report technique scores, or invent evidence. A detailed change ledger, validation plan, or routine list of five techniques is unnecessary.

Stop after returning the brief. Performing the task is a separate downstream request.

## Keep the boundary

This skill does not write logs, capture briefs to disk, calculate hashes, run comparisons, maintain evidence, or update itself. It needs no backend process, data directory, or separate API key. Recording and evaluation belong to the optional BriefBench backend.

Extracting reusable prompting claims from articles also belongs to backend source intake. Reading a referenced article to understand the particular prompt is different from building a technique registry. If asked for intake or evaluation rather than prompt improvement, state that it is outside this skill; do not pretend an unbuilt backend capability is available.
