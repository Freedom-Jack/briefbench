import pytest

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
                                  "`NOT STATED`", "Skip"])
def test_skip_markers(body):
    assert is_skip(body)


@pytest.mark.parametrize("body", ["Not stated in the prompt, but the answer says the API must stay stable.",
                                  "None of the existing tests may be changed.",
                                  "No payment confirmation may be lost.",
                                  "Not stated. However, keep Python 3.11 support.",
                                  "#1 priority: payments must never be lost."])
def test_real_sections_are_not_skipped(body):
    assert not is_skip(body)


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
    reply = ("x " * 300) + "<background-and-why>\n" + ("word " * 160) + "\n```sh\nrm -rf /\n```\n</background-and-why>"
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


def test_rewriter_hash_is_stable():
    assert rewriter_sha256() == rewriter_sha256() and len(rewriter_sha256()) == 64


def test_assemble_brief_without_sections():
    assert assemble_brief("p", []) == "p\n"


def test_messages_built_from_answers():
    answers = dict(NONE, verify=Answer("pytest -q passes", "asked"))
    _, user = build_messages(PROMPT, answers, TECH)
    assert "<answer_verify>\npytest -q passes\n</answer_verify>" in user.content
