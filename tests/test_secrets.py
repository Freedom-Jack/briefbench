from briefbench.presets import secret_values
from briefbench.redact import scrub, strip_controls
from conftest import KEY


def test_scrub_is_exact_only():
    assert scrub("***bold*** and ollama", ["ollama", KEY]) == "***bold*** and ollama"
    assert scrub(f'{{"k":"{KEY}"}}', [KEY]) == '{"k":"[redacted]"}'
    assert scrub('{"k":"a\\"b-0123456789"}', ['a"b-0123456789']) == '{"k":"[redacted]"}'   # JSON-escaped form too


def test_secret_values_are_the_set_key_variables():
    environ = {"OPENAI_API_KEY": f" {KEY} ", "GEMINI_API_KEY": "short", "ANTHROPIC_API_KEY": "", "OTHER": KEY + "x"}
    assert secret_values(environ) == [KEY]


def test_terminal_controls_are_stripped():
    assert strip_controls("ok\x1b]0;title\x07 \x9b2J\tdone\n") == "ok]0;title 2J\tdone\n"
