"""The three questions, and how they are asked. Vendor-neutral."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Mapping


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    hint: str
    flag: str


QUESTIONS = (
    Question("why", "Why do you want this?", "What should happen once it's done?", "--why"),
    Question("stretch", "What would a stretch result look like?",
             "Beyond what you strictly need; your real goal stays the bar.", "--stretch"),
    Question("verify", "How will the result be verified?",
             "By something other than the model: a test, a command, data, or a person.", "--verify"),
)

Source = Literal["flag", "asked", "skipped", "not_asked"]


@dataclass(frozen=True)
class Answer:
    text: str | None     # None: no answer
    source: Source


def collect_answers(flags: Mapping[str, str | None], *, ask: bool, not_asked_reason: str | None,
                    stdin, write: Callable[[str], None]) -> dict[str, Answer]:
    """flags maps a question id to its flag value (None = flag not given).
    ask: stdin and stderr are terminals and -n was not given.
    not_asked_reason: why questions can't be asked, or None to stay silent (for -n)."""
    answers: dict[str, Answer] = {}
    pending = []
    for q in QUESTIONS:
        value = flags.get(q.id)
        if value is None:
            pending.append(q)
        else:
            text = value.strip() or None
            answers[q.id] = Answer(text, "flag" if text else "skipped")
    if pending and not ask:
        for q in pending:
            answers[q.id] = Answer(None, "not_asked")
        if not_asked_reason:
            write(f"Not asked ({not_asked_reason}): {_join([q.id for q in pending])}. Answer with "
                  f"{_join([q.flag for q in pending])}, or pass -n to silence this.\n")
        return {q.id: answers[q.id] for q in QUESTIONS}
    if pending:
        n = len(pending)
        write(f"\n{n} question{'s' if n > 1 else ''}. Press Enter to skip one, for example when your prompt "
              "already answers it, or Ctrl-D to skip the rest.\n")
    for i, q in enumerate(pending, 1):
        write(f"\n[{i}/{len(pending)}] {q.text} ({q.hint})\n> ")
        line = stdin.readline()            # not input(): input() writes its prompt to stdout
        if line == "":                     # Ctrl-D: skip this question and the rest
            write("\n")
            for rest in pending[i - 1:]:
                answers[rest.id] = Answer(None, "skipped")
            break
        text = line.strip() or None
        answers[q.id] = Answer(text, "asked" if text else "skipped")
    if pending:
        write("\n")
    return {q.id: answers[q.id] for q in QUESTIONS}


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
