import pytest

from briefbench.playbook import load_playbook
from briefbench.provider import ProviderInfo
from briefbench.questions import Answer
from briefbench.report import HONESTY, render_report
from briefbench.rewrite import rewrite
from conftest import FakeProvider

PROMPT = "Add retry logic to the payment webhook handler"
INFO = ProviderInfo(name="gemini", vendor="google", base_url="https://x.invalid/v1", model="fake-model",
                    key_env="GEMINI_API_KEY", token_param="max_tokens", chosen_by="--provider")


@pytest.mark.parametrize("verify,note", [(Answer(None, "not_asked"), "(nothing to add; unanswered: verify)"),
                                         (Answer("V", "flag"), "(skipped, although you answered: verify)")])
def test_golden_report(verify, note):
    answers = {"why": Answer("W", "flag"), "stretch": Answer(None, "skipped"), "verify": verify}
    result = rewrite(FakeProvider(), PROMPT, answers, load_playbook().active())
    assert render_report(PROMPT, result, answers, INFO, "0f1e2d3c-0000-4000-8000-000000000000",
                         "~/.briefbench/log.jsonl") == (
        "What changed: 3 of 5 techniques added a section below your prompt (8 -> 45 words).\n"
        "  added    Background and why              on trial, no comparisons yet\n"
        "  added    Outcome with a stretch target   on trial, no comparisons yet\n"
        f"  skipped  Verification outside the model  on trial, no comparisons yet  {note}\n"
        "  added    Definition of done              on trial, no comparisons yet\n"
        "  missing  Constraints and non-goals       on trial, no comparisons yet  (no section in the reply)\n"
        "None of these techniques has a record on your tasks yet, so this brief is an untested hypothesis, "
        "not a proven improvement.\n"
        "fake-model (answered by fake-model-2026-10) via gemini, 0.0 s, 100 tokens in, 50 out\n"
        "Logged as 0f1e2d3c-0000-4000-8000-000000000000 in ~/.briefbench/log.jsonl")


def test_nothing_added_and_warnings():
    reply = "".join(f"<{t.id}>N/A</{t.id}>" for t in load_playbook().active()) + "x" * 300
    answers = {q: Answer(None, "not_asked") for q in ("why", "stretch", "verify")}
    result = rewrite(FakeProvider(reply), PROMPT, answers, load_playbook().active())
    text = render_report(PROMPT, result, answers, INFO, "id", None)
    assert "Nothing was added, so the brief is your prompt as written." in text
    assert "Answering the questions gives the rewriter something to work from." in text
    assert "Warning: the model wrote text outside its sections; it was ignored." in text
    assert text.endswith("Not logged.")


def test_nothing_added_although_every_question_was_answered():
    reply = "".join(f"<{t.id}>NOT STATED</{t.id}>" for t in load_playbook().active()[1:])
    answers = {q: Answer("an answer", "flag") for q in ("why", "stretch", "verify")}
    result = rewrite(FakeProvider(reply), PROMPT, answers, load_playbook().active())
    assert render_report(PROMPT, result, answers, INFO, "id", None).splitlines()[:8] == [
        "What changed: 0 of 5 techniques added a section below your prompt (8 -> 8 words).",
        "  missing  Background and why              on trial, no comparisons yet  "
        "(no section in the reply, although you answered: why)",
        "  skipped  Outcome with a stretch target   on trial, no comparisons yet  "
        "(skipped, although you answered: why, stretch)",
        "  skipped  Verification outside the model  on trial, no comparisons yet  "
        "(skipped, although you answered: verify)",
        "  skipped  Definition of done              on trial, no comparisons yet  (the rewriter found nothing to add)",
        "  skipped  Constraints and non-goals       on trial, no comparisons yet  (the rewriter found nothing to add)",
        "Nothing was added, so the brief is your prompt as written.",
        HONESTY]
