"""The "what changed" report printed to stderr after the brief. Vendor-neutral."""
from __future__ import annotations

from typing import Mapping

from .playbook import Technique
from .provider import ProviderInfo
from .questions import Answer
from .rewrite import RewriteResult

HONESTY = ("None of these techniques has a record on your tasks yet, so this brief is an untested "
           "hypothesis, not a proven improvement.")


def record(technique: Technique) -> str:
    """Stage 1 runs no comparisons. Stage 3 replaces this with wins, losses and ties and the
    significance verdict, computed from judged log entries."""
    return f"{technique.status_label}, no comparisons yet"


def words(text: str) -> int:
    return len(text.split())


def render_report(prompt: str, result: RewriteResult, answers: Mapping[str, Answer], info: ProviderInfo,
                  entry_id: str, log_display: str | None) -> str:
    sections = result.sections
    added = sum(s.result == "added" for s in sections)
    lines = [f"What changed: {added} of {len(sections)} techniques added a section below your prompt "
             f"({words(prompt)} -> {words(result.brief)} words)."]
    width = max(len(s.technique.name) for s in sections)
    for s in sections:
        t = s.technique
        note = ""
        answered = [q for q in t.uses_answers if answers[q].text]
        unanswered = [q for q in t.uses_answers if not answers[q].text]
        if s.result == "skipped":
            note = (f"  (nothing to add; unanswered: {', '.join(unanswered)})" if unanswered
                    else f"  (skipped, although you answered: {', '.join(answered)})" if answered
                    else "  (the rewriter found nothing to add)")
        elif s.result == "missing":
            note = (f"  (no section in the reply, although you answered: {', '.join(answered)})" if answered
                    else "  (no section in the reply)")
        lines.append(f"  {s.result:<8} {t.name:<{width}}  {record(t)}{note}")
    if added == 0:
        lines.append("Nothing was added, so the brief is your prompt as written." +
                     ("" if all(a.text for a in answers.values()) else
                      " Answering the questions gives the rewriter something to work from."))
    for w in result.warnings:
        lines.append(f"Warning: {w}")
    lines.append(HONESTY)
    c = result.completion
    model = c.model_reported or f"{info.model} (model not reported)"
    if c.model_reported and c.model_reported != info.model:
        model = f"{info.model} (answered by {c.model_reported})"
    stats = [f"{model} via {info.name}", f"{c.latency_ms / 1000:.1f} s"]
    if c.attempts > 1:
        stats.append(f"{c.attempts} attempts")
    u = c.usage
    if u.input_tokens is not None and u.output_tokens is not None:
        reasoning = f" (incl. {u.reasoning_tokens:,} reasoning)" if u.reasoning_tokens else ""
        stats.append(f"{u.input_tokens:,} tokens in, {u.output_tokens:,} out{reasoning}")
    lines.append(", ".join(stats))
    lines.append(f"Logged as {entry_id} in {log_display}" if log_display else "Not logged.")
    return "\n".join(lines)
