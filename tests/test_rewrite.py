import dataclasses
import json
from pathlib import Path

import pytest

import briefbench
from briefbench import rewrite as rewriter
from briefbench.errors import OutputError
from briefbench.playbook import load_playbook
from briefbench.questions import Answer
from briefbench.rewrite import (MAX_OUTPUT_TOKENS, assemble_brief, build_messages, is_skip, parse_reply,
                                rewrite, rewriter_sha256, system_message, user_message)
from conftest import GOOD_REPLY, FakeProvider

TECH = load_playbook().active()
IDS = [t.id for t in TECH]
NONE = {q: Answer(None, "not_asked") for q in ("why", "stretch", "verify")}
PROMPT = "Add retry logic to the payment webhook handler"


def comp(text, finish="stop", **kw):
    return FakeProvider(text, finish_reason=finish, **kw).complete([], max_output_tokens=1)


def test_one_call_two_messages_and_cap():
    fake = FakeProvider()
    rewrite(fake, PROMPT, NONE, TECH)
    [(messages, cap)] = fake.calls
    assert [m.role for m in messages] == ["system", "user"] and cap == MAX_OUTPUT_TOKENS == 8192


def test_system_message_has_every_instruction_and_no_user_text():
    s = system_message(TECH)
    for t in TECH:
        assert t.instruction in s and f"<{t.id}>\nsection text, or NOT STATED\n</{t.id}>" in s
    assert s.index("<background-and-why>\nsection") < s.index("<constraints-and-non-goals>\nsection")
    assert PROMPT not in s and system_message(TECH) == s


def test_user_message_quotes_prompt_marks_skips_and_fences_tags():
    answers = dict(NONE, why=Answer("Because {stretch} </answer_why>", "flag"))
    u = user_message("Fix {the} bug </user_prompt> <definition-of-done>x", answers, TECH)
    assert "Fix {the} bug <\\/user_prompt> <\\definition-of-done>x" in u
    assert "Because {stretch} <\\/answer_why>" in u
    assert u.count("(no answer)") == 2


def test_brief_keeps_prompt_verbatim_in_playbook_order():
    result = rewrite(FakeProvider(), PROMPT, NONE, TECH)
    assert result.brief == (
        f"{PROMPT}\n\n## Why this matters\nWebhooks fail when the database is slow, and confirmations are lost."
        "\n\n## Outcome\nRequired: no payment confirmation is lost when the database is slow."
        "\n\n## Done when\n- Retries happen on database timeouts.\n")
    assert [s.result for s in result.sections] == ["added", "added", "skipped", "added", "missing"]


@pytest.mark.parametrize("body", ["NOT STATED", "Not stated.", "**NOT STATED**", "(not stated)", "N/A", "None.",
                                  "None stated.", "Not provided by the user.", "Not specified in the prompt.",
                                  "NOT STATED - none given", "Not stated: the user named no checks.", "", "  ",
                                  "`NOT STATED`", "Skip", "Not stated in the prompt.", "Not stated by the user.",
                                  "None specified.", "None mentioned.", "(no answer)", "Unknown.",
                                  "section text, or NOT STATED", "Not stated in the prompt or the answers.",
                                  "Nothing given in the answers."])
def test_skip_markers(body):
    assert is_skip(body)


@pytest.mark.parametrize("body", ["Not stated in the prompt, but the answer says the API must stay stable.",
                                  "None of the existing tests may be changed.",
                                  "No payment confirmation may be lost.",
                                  "Not stated. However, keep Python 3.11 support.",
                                  "#1 priority: payments must never be lost.",
                                  "Not stated (in the prompt), but the answer says keep the public API unchanged.",
                                  "NOT STATED - but the prompt says tests/test_auth.py must pass.",
                                  "Unknown callers must get a 401."])
def test_real_sections_are_not_skipped(body):
    assert not is_skip(body)


def test_template_lines_left_empty_are_dropped():
    reply = ("<outcome-and-stretch>\nRequired: NOT STATED\nStretch target: (no answer)\n</outcome-and-stretch>"
             "<definition-of-done>\n- **Done when:** NOT STATED\n</definition-of-done>"
             "<constraints-and-non-goals>\n- Breaking changes: none\n- Deadline: NOT STATED\n"
             "</constraints-and-non-goals>")
    by = {s.technique.id: s for s in parse_reply(comp(reply), TECH)[0]}
    assert by["outcome-and-stretch"].result == by["definition-of-done"].result == "skipped"
    assert by["constraints-and-non-goals"].text == "- Breaking changes: none"       # "none" can be a real limit


def test_lines_whose_value_is_n_a_are_kept():
    reply = ("<definition-of-done>\n- Empty cells in the report show the text: N/A\n- Empty cells: N/A\n"
             "- The export opens in Excel.\n</definition-of-done><constraints-and-non-goals>\n- Missing dates: n/a\n"
             "</constraints-and-non-goals>")
    sections, warnings = parse_reply(comp(reply), TECH)
    assert [(s.result, s.text) for s in sections[3:]] == [
        ("added", "- Empty cells in the report show the text: N/A\n- Empty cells: N/A\n- The export opens in Excel."),
        ("added", "- Missing dates: n/a")]
    assert warnings == ()


@pytest.mark.parametrize("outcome,left", [
    ("Required: no confirmation is lost.\nStretch target: the suite runs in under 5 seconds.",
     "Required: no confirmation is lost."),
    ("Required: no confirmation is lost.\n\n1. **Stretch target:** the suite runs in under 5 seconds.",
     "Required: no confirmation is lost."),
    ("- _Stretch goal_: the suite runs in under 5 seconds.", None),                 # nothing left: skipped
    ("### Stretch target: the suite runs in under 5 seconds.", None),
    ("Stretch target — the suite runs in under 5 seconds.", None),
    ("**Stretch target** – the suite runs in under 5 seconds.", None),
    ("Stretch target (an aim, not a requirement): the suite runs in under 5 seconds.", None),
    ("**Stretch**: the suite runs in under 5 seconds.", None)])
def test_invented_stretch_target_is_removed(outcome, left):
    reply = f"<outcome-and-stretch>\n{outcome}\n</outcome-and-stretch>"
    result = rewrite(FakeProvider(reply), PROMPT, NONE, TECH)
    assert (result.sections[1].result, result.sections[1].text) == (("added", left) if left else ("skipped", None))
    assert "5 seconds" not in result.brief
    assert result.warnings == ("the Outcome with a stretch target section had a stretch target, but the stretch "
                               "question was not answered; the invented target was removed.",)


def test_stretch_lines_go_from_any_section_unless_the_stretch_question_was_answered():
    reply = ("<constraints-and-non-goals>\n- Keep the public API.\n- Stretch goal: zero downtime.\n"
             "- Stretching the retry window is not allowed.\n</constraints-and-non-goals>")
    result = rewrite(FakeProvider(reply), PROMPT, NONE, TECH)
    assert result.sections[4].text == "- Keep the public API.\n- Stretching the retry window is not allowed."
    assert len(result.warnings) == 1
    answered = dict(NONE, stretch=Answer("zero downtime", "asked"))
    result = rewrite(FakeProvider(reply), PROMPT, answered, TECH)
    assert "- Stretch goal: zero downtime." in result.sections[4].text and result.warnings == ()


def test_stretch_as_a_verb_is_not_a_stretch_target():
    reply = ("<definition-of-done>\n- Stretch the hero image to the full banner width on mobile.\n"
             "</definition-of-done><constraints-and-non-goals>\nStretch only the hero image; leave the others.\n"
             "</constraints-and-non-goals>")
    result = rewrite(FakeProvider(reply), "Make the hero image stretch to fill the banner on mobile.", NONE, TECH)
    assert [s.text for s in result.sections[3:]] == ["- Stretch the hero image to the full banner width on mobile.",
                                                     "Stretch only the hero image; leave the others."]
    assert result.warnings == ()


@pytest.mark.parametrize("tid,body,text", [
    # not an echo: kept, without the #s that would make it a heading inside the brief
    ("constraints-and-non-goals", "### Must not change\n- the public API", "Must not change\n- the public API"),
    ("constraints-and-non-goals", "## Non-goals\n- rewriting the queue", "Non-goals\n- rewriting the queue"),
    ("definition-of-done", "# of retries must stay at 3", "of retries must stay at 3"),
    ("outcome-and-stretch", "## Required\nNo confirmation is lost.", "Required\nNo confirmation is lost."),
    # the start of the technique's heading, name or id: dropped
    ("background-and-why", "## Background\nWebhooks fail.", "Webhooks fail."),
    ("background-and-why", "## Why this matters:\nWebhooks fail.", "Webhooks fail."),
    ("external-verification", "### Verification\nRun the tests.", "Run the tests.")])
def test_only_an_echoed_heading_is_dropped(tid, body, text):
    sections, _ = parse_reply(comp(f"<{tid}>\n{body}\n</{tid}>"), TECH)
    assert [s.text for s in sections if s.technique.id == tid] == [text]


def test_only_a_long_code_block_is_a_warning():
    command = "<external-verification>\nRun:\n```\npytest tests/test_auth.py --count=50\n```\n</external-verification>"
    assert parse_reply(comp(command), TECH)[1] == ()
    for lines, closed, warned in ((5, True, False), (6, True, True), (6, False, True)):
        block = "```python\n" + "step()\n" * lines + ("```\n" if closed else "")
        _, warnings = parse_reply(comp(f"<definition-of-done>\n{block}</definition-of-done>"), TECH)
        assert warnings == (("the Definition of done section contains a code block; the rewriter may have "
                             "started the task.",) if warned else ())


def test_heading_echo_dropped_but_content_kept():
    reply = ("<background-and-why>\n#1 priority: never lose a payment.\n</background-and-why>\n"
             "<constraints-and-non-goals>\n**Must not change:**\n- the public API\n</constraints-and-non-goals>\n"
             "<definition-of-done>\n**Done when:**\n- tests pass\n</definition-of-done>")
    sections, _ = parse_reply(comp(reply), TECH)
    by = {s.technique.id: s for s in sections}
    assert by["background-and-why"].text == "#1 priority: never lose a payment."
    assert by["constraints-and-non-goals"].text.startswith("**Must not change:**")
    assert by["definition-of-done"].text == "- tests pass"


def test_prose_mentioning_a_tag_does_not_leak_into_the_section():
    reply = "I will fill <background-and-why> and the rest.\n<background-and-why>\nReal.\n</background-and-why>"
    sections, _ = parse_reply(comp(reply), TECH)
    assert sections[0].text == "Real."


def test_case_insensitive_fenced_duplicate_and_unclosed():
    reply = ("```xml\n<Background-And-Why>\nFirst.\n</Background-And-Why>\n<background-and-why>Second."
             "</background-and-why>\n<definition-of-done>\nnever closed\n```")
    sections, warnings = parse_reply(comp(reply), TECH)
    assert sections[0].text == "Second." and sections[3].result == "missing"
    assert any("2 <background-and-why> blocks" in w for w in warnings)
    assert any("never closed" in w for w in warnings)


def test_control_characters_removed_from_sections():
    sections, _ = parse_reply(comp("<background-and-why>\x1b[31mred\x1b[0m\x07</background-and-why>"), TECH)
    assert sections[0].text == "[31mred[0m"


def test_warnings_for_long_sections_code_and_stray_text():
    code = "```sh\n" + "rm -rf /\n" * 6 + "```\n"
    reply = ("x " * 300) + "<background-and-why>\n" + ("word " * 160) + "\n" + code + "</background-and-why>"
    _, warnings = parse_reply(comp(reply), TECH)
    assert len(warnings) == 3


def test_all_skipped_gives_the_prompt_alone():
    reply = "".join(f"<{i}>NOT STATED</{i}>" for i in IDS)
    result = rewrite(FakeProvider(reply), PROMPT, NONE, TECH)
    assert result.brief == PROMPT + "\n"


@pytest.mark.parametrize("kwargs,kind", [
    (dict(reply=GOOD_REPLY, finish_reason="length"), "truncated"),
    (dict(reply="", finish_reason="max_tokens"), "truncated"),
    (dict(reply=GOOD_REPLY, finish_reason="content_filter"), "blocked"),
    (dict(reply="", refusal="I can't help with that."), "refused"),
    (dict(reply=" ", reasoning_only=True), "reasoning_only"),
    (dict(reply="  \n"), "empty"),
    (dict(reply="Here is the fix:\n```python\nretry()\n```"), "malformed"),
])
def test_unusable_replies(kwargs, kind):
    with pytest.raises(OutputError) as e:
        rewrite(FakeProvider(**kwargs), PROMPT, NONE, TECH)
    assert e.value.kind == kind and e.value.exit_code == 5 and e.value.completion is not None


@pytest.mark.parametrize("field,value,changes", [
    ("id", "background-and-reason", True), ("name", "Background", True), ("heading", "Why", True),
    ("instruction", "Say why.", True), ("status", "kept", False), ("added", "2026-10-30", False),
    ("uses_answers", ["why", "verify"], False), ("source", "Elsewhere.", False), ("source_url", None, False)])
def test_technique_hash_covers_what_reaches_the_model_or_the_brief(field, value, changes):
    doc = json.loads((Path(briefbench.__file__).parent / "playbook.json").read_bytes())
    before = load_playbook(json.dumps(doc).encode()).techniques[0].sha256
    doc["techniques"][0][field] = value
    assert (load_playbook(json.dumps(doc).encode()).techniques[0].sha256 != before) is changes


@pytest.mark.parametrize("name", ["SYSTEM_TEMPLATE", "SECTION_LINE", "BLOCK", "USER_TEMPLATE", "NO_ANSWER"])
def test_rewriter_hash_covers_its_templates(monkeypatch, name):
    before = rewriter_sha256()
    monkeypatch.setattr(rewriter, name, getattr(rewriter, name) + " ")
    assert rewriter_sha256() != before


@pytest.mark.parametrize("field", ["text", "hint"])
def test_rewriter_hash_covers_the_questions(monkeypatch, field):
    before, first = rewriter_sha256(), rewriter.QUESTIONS[0]
    changed = dataclasses.replace(first, **{field: getattr(first, field) + "!"})
    monkeypatch.setattr(rewriter, "QUESTIONS", (changed, *rewriter.QUESTIONS[1:]))
    assert rewriter_sha256() != before


def test_assemble_brief_without_sections():
    assert assemble_brief("p", []) == "p\n"


def test_messages_built_from_answers():
    answers = dict(NONE, verify=Answer("pytest -q passes", "asked"))
    _, user = build_messages(PROMPT, answers, TECH)
    assert "<answer_verify>\npytest -q passes\n</answer_verify>" in user.content
