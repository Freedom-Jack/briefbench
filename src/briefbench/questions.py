"""The three questions, and how they are asked. Vendor-neutral."""
from __future__ import annotations

import contextlib
import functools
import os
import re
import select
import unicodedata
from dataclasses import dataclass
from typing import Callable, Iterator, Literal, Mapping

from .errors import UsageError

try:
    import fcntl
    import termios
except ImportError:      # Windows: a terminal is read like any other input
    fcntl = termios = None

PASTE_GAP_S = 0.05       # lines that arrive this close together are one paste
ANSWER_PROMPT = "> "     # shown before each answer
_KEYS = re.compile(rb"\x1b(?:\[[0-?]*[ -/]*[@-~]|O.)?|[\x00-\x08\x0a-\x1f\x7f]", re.S)   # arrow keys etc.; Tab is text


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
        with line_mode_off(stdin) as read:      # from the first question on, so no answer waits in line mode
            write(f"\n{n} question{'s' if n > 1 else ''}. Answers are one line; longer ones go in "
                  f"{_join([q.flag for q in pending])}. Press Enter to skip one, for example when your prompt "
                  "already answers it, or Ctrl-D to skip the rest.\n")
            for i, q in enumerate(pending, 1):
                write(f"\n[{i}/{n}] {q.text} ({q.hint})\n{ANSWER_PROMPT}")
                line = _read_answer(stdin, read)
                if line == "":                  # Ctrl-D: skip this question and the rest
                    write("\n")
                    for rest in pending[i - 1:]:
                        answers[rest.id] = Answer(None, "skipped")
                    break
                text = line.strip() or None
                answers[q.id] = Answer(text, "asked" if text else "skipped")
        write("\n")
    return {q.id: answers[q.id] for q in QUESTIONS}


def _read_answer(stdin, read) -> str:
    """One answer, or "" for Ctrl-D."""
    try:                                   # not input(): it writes to stdout
        text = stdin.readline() if read is None else read(answer=True).decode("utf-8")
        text.encode("utf-8")               # lone surrogates: bytes that are not UTF-8, read with surrogateescape
    except (UnicodeDecodeError, UnicodeEncodeError):
        raise UsageError("an answer is not valid UTF-8. Check your terminal's encoding, or give the answer "
                         "with --why, --stretch or --verify.") from None
    return text


@contextlib.contextmanager
def line_mode_off(stdin) -> Iterator[Callable[..., bytes] | None]:
    """Turns the terminal's line mode off while the block runs, because it holds at most 1,024 bytes per line
    on macOS and a longer line would hang. Yields read (see _read), or None if stdin is not a terminal.
    Afterwards the terminal is set back, and input still waiting is thrown away, so it never becomes an
    answer or reaches the shell once briefbench exits."""
    fd = None
    if termios is not None:
        try:
            fd = stdin.fileno()
            saved, raw = termios.tcgetattr(fd), termios.tcgetattr(fd)
            # echoed by _read, so erasing shows; left to the terminal if echo is off or the descriptor is read-only
            echo = bool(saved[3] & termios.ECHO) and (fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE) != os.O_RDONLY
        except (OSError, ValueError, AttributeError, termios.error):    # not a terminal, or a test double
            fd = None
    if fd is None:
        yield None
        return
    raw[3] &= ~(termios.ICANON | (termios.ECHO if echo else 0))    # ISIG stays on, for Ctrl-C
    raw[6][termios.VMIN], raw[6][termios.VTIME] = 1, 0
    try:
        termios.tcsetattr(fd, termios.TCSANOW, raw)
        yield functools.partial(_read, fd, echo)
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSANOW, saved)
        except termios.error:
            pass
        discard_typeahead(stdin)


def _read(fd: int, echo: bool, *, answer: bool) -> bytes:
    """What is typed or pasted. Backspace, Ctrl-U and Ctrl-W edit the current line, on screen too; other
    control keys are ignored, and Ctrl-C still works.
    An answer ends at Enter, or is b"" for Ctrl-D before any text. The lines of a paste stay in one answer,
    whether or not the paste ends with a line break, so none of them answers a later question.
    A prompt ends at Ctrl-D, anywhere, and what follows is dropped."""
    data = bytearray()
    while True:
        chunk = os.read(fd, 4096)
        shown, ctrl_d = _edit(data, chunk, len(ANSWER_PROMPT) if answer else 0)
        if answer and ctrl_d and data and not data.endswith(b"\n"):
            shown += b"\n"                                         # Ctrl-D after text ends the answer, as Enter
        if echo:
            _show(fd, shown)
        if ctrl_d or not chunk:                                    # or the terminal hung up
            return bytes(data)
        if answer and data.endswith(b"\n") and not select.select([fd], [], [], PASTE_GAP_S)[0]:
            return bytes(data)                                     # Enter, with no more of a paste behind it


def _edit(data: bytearray, chunk: bytes, column: int) -> tuple[bytes, bool]:
    """Adds typed or pasted bytes to data, as line mode would. Returns what to echo, and whether Ctrl-D was
    pressed; what follows it is dropped. column: where the first line starts on screen."""
    shown, start = bytearray(), 0
    for key in _KEYS.finditer(chunk):
        text, start, key = chunk[start:key.start()], key.end(), key.group()
        data += text
        shown += text
        if key == b"\x04":                                         # Ctrl-D
            return bytes(shown), True
        if key in (b"\n", b"\r"):
            data += b"\n"
            shown += b"\n"
        elif key in (b"\x7f", b"\x08", b"\x15", b"\x17"):          # Backspace (two codes), Ctrl-U, Ctrl-W
            shown += _erase(data, key, column)
    data += chunk[start:]
    shown += chunk[start:]
    return bytes(shown), False


def _erase(data: bytearray, key: bytes, column: int) -> bytes:
    """Erases from the current line of data, never past its start: a character for Backspace, the line for
    Ctrl-U, or the spaces and word before the cursor for Ctrl-W. Returns what erases it on screen."""
    start = data.rfind(b"\n") + 1
    line = bytes(data[start:])
    if key == b"\x15":
        keep = 0
    elif key == b"\x17":
        keep = len(line.rstrip(b" \t"))
        while keep and line[keep - 1] not in b" \t":
            keep -= 1
    else:
        keep = max(len(line) - 1, 0)
        while keep and line[keep] & 0xC0 == 0x80:                  # back to the first byte of a UTF-8 character
            keep -= 1
    del data[start + keep:]
    first = column if start == 0 else 0
    n = _column(line, first) - _column(line[:keep], first)
    return b"\b" * n + b" " * n + b"\b" * n


def _column(text: bytes, column: int) -> int:
    """The screen column after text is shown from column on: tabs, wide characters and accents counted."""
    for ch in text.decode("utf-8", "replace"):
        if ch == "\t":
            column += 8 - column % 8
        elif not unicodedata.combining(ch):
            column += 2 if unicodedata.east_asian_width(ch) in "WF" else 1
    return column


def _show(fd: int, data: bytes) -> None:
    try:
        while data:
            data = data[os.write(fd, data):]
    except OSError:                        # the terminal has gone: there is no one to show it to
        pass


def discard_typeahead(stdin) -> None:
    """Throw away input still waiting on a terminal, such as the end of a paste, so it never reaches
    the shell once briefbench exits. Does nothing for other input."""
    if termios is None:
        return
    try:
        fd = stdin.fileno()
        if os.isatty(fd):
            termios.tcflush(fd, termios.TCIFLUSH)
    except (OSError, ValueError, AttributeError, termios.error):
        pass


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
