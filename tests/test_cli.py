import io

from briefbench import __version__, cli


def test_version_and_missing_command(capsys):
    assert cli.run(["--version"]) == 0 and capsys.readouterr().out.strip() == f"briefbench {__version__}"
    err = io.StringIO()
    assert cli.run([], stderr=err) == 2 and "no commands yet" in err.getvalue()


def test_abbreviated_flags_rejected():
    assert cli.run(["--vers"], stderr=io.StringIO()) == 2


def test_keys_mistyped_into_flags_are_not_echoed(monkeypatch, capsys):
    key = "sk-proj-FLAG-0123456789abcdef"
    monkeypatch.setenv("OPENAI_API_KEY", key)
    for argv in (["--api-key=" + key], [key]):
        assert cli.run(argv, stderr=io.StringIO()) == 2
    shown = capsys.readouterr()
    assert key not in shown.out + shown.err and "[redacted]" in shown.err


def test_a_reader_that_has_gone_does_not_change_the_outcome():
    class Gone(io.StringIO):         # `2>&1 | head -0`: the pipe is already closed
        def write(self, text):
            raise BrokenPipeError(32, "Broken pipe")

    assert cli.run([], stderr=Gone()) == 2
