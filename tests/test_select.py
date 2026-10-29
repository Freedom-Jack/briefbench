import pytest

from briefbench.errors import ConfigError, UsageError
from briefbench.selection import select_provider


def select(**kwargs):
    args = dict(provider=None, model=None, base_url=None, api_key_env=None, timeout_s=1, environ={})
    args.update(kwargs)
    return select_provider(**args)


@pytest.mark.parametrize("kwargs,environ,expect", [
    (dict(), {}, ConfigError), (dict(), {"GEMINI_API_KEY": "g" * 12}, "gemini"),
    (dict(), {"GEMINI_API_KEY": "g" * 12, "OPENAI_API_KEY": "o" * 12}, "gemini"),
    (dict(), {"ANTHROPIC_API_KEY": "a" * 12, "GEMINI_API_KEY": "g" * 12}, "anthropic"),
    (dict(), {"GEMINI_API_KEY": "   "}, ConfigError),
    (dict(provider="openai"), {}, ConfigError), (dict(base_url="http://127.0.0.1:1/v1"), {}, UsageError),
    (dict(base_url="http://127.0.0.1:1/v1", model="m"), {}, "custom"),
    (dict(api_key_env="MY_KEY"), {"MY_KEY": "k" * 12}, UsageError),
    (dict(provider="gemini", api_key_env="GOOGLE_API_KEY"), {"GOOGLE_API_KEY": "k" * 12}, "gemini"),
    (dict(provider="openai", api_key_env="sk-proj-abc"), {}, UsageError),
    (dict(provider="openai"), {"OPENAI_API_KEY": "sk-a b-12345678"}, ConfigError),
    (dict(provider="openai"), {"OPENAI_API_KEY": "sk-line\nbreak-12345678"}, ConfigError),
    (dict(base_url="http://10.0.0.5/v1", model="m", api_key_env="MY_KEY"), {"MY_KEY": "k" * 12}, UsageError),
    (dict(base_url="http://[::1]:8080/v1", model="m", api_key_env="MY_KEY"), {"MY_KEY": "k" * 12}, "custom"),
    (dict(base_url="http://10.0.0.5/v1", model="m"), {}, "custom"),
    (dict(base_url="https://u:p@host/v1", model="m"), {}, UsageError),
    (dict(base_url="https://host/v1?key=sk-123", model="m"), {}, UsageError),
    (dict(base_url="ftp://host/v1", model="m"), {}, UsageError),
    (dict(base_url="https://host:99999/v1", model="m"), {}, UsageError),
])
def test_select_provider(kwargs, environ, expect):
    if isinstance(expect, str):
        assert select(environ=environ, **kwargs).info.name == expect
    else:
        with pytest.raises(expect) as e:
            select(environ=environ, **kwargs)
        assert "sk-" not in str(e.value) and "u:p" not in str(e.value)


def test_selection_details():
    with pytest.raises(UsageError, match="--base-url needs --model"):
        select(base_url="http://127.0.0.1:1/v1")
    custom = select(base_url="http://127.0.0.1:1/v1/", model="m")
    assert (custom.api_key, custom.info.key_env, custom.info.vendor) == (None, None, None)
    assert custom.info.base_url == "http://127.0.0.1:1/v1" and custom.info.params == {}
    named = select(provider="gemini", api_key_env="GOOGLE_API_KEY", environ={"GOOGLE_API_KEY": " k-123456789 "})
    assert (named.info.key_env, named.api_key, named.info.chosen_by) == ("GOOGLE_API_KEY", "k-123456789", "--provider")
    auto = select(environ={"GEMINI_API_KEY": "g" * 12, "OPENAI_API_KEY": "o" * 12})
    assert auto.info.chosen_by == "auto: GEMINI_API_KEY is set" and auto.others == ("OPENAI_API_KEY",)
    assert "g" * 12 not in repr(auto)
    dry = select(provider="openai", require_key=False)
    assert dry.api_key is None and dry.info.params == {"reasoning_effort": "low"}
