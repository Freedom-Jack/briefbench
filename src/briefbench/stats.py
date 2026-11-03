"""The exact sign test, the Clopper-Pearson interval and the two-step rule, in plain Python. Vendor-neutral."""
from __future__ import annotations

from math import comb


def sign_test(wins: int, losses: int) -> float:
    """Exact two-sided p-value of wins against losses, ties left out."""
    n = wins + losses
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(wins, losses) + 1)) / 2 ** n)


def _at_most(k: int, n: int, p: float) -> float:
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def interval(wins: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Clopper-Pearson interval for the win rate, by bisection on the binomial."""
    if n == 0:
        return 0.0, 1.0
    tail = (1 - level) / 2

    def bisect(too_low) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if too_low(mid) else (lo, mid)
        return (lo + hi) / 2

    lower = 0.0 if wins == 0 else bisect(lambda p: 1 - _at_most(wins - 1, n, p) < tail)
    upper = 1.0 if wins == n else bisect(lambda p: _at_most(wins, n, p) > tail)
    return lower, upper


def decide(winners: list[str], trials: int, rule: dict) -> tuple[str, int, int]:
    """The two-step rule on B's wins (docs/design.md, "Protocol"). winners: "a" or "b" for each decided pair, in the
    order they were run; trials counts ties too. Returns (state, B's wins, pairs) for the pairs the rule looked at.
    state is adopt, stop, continue, collecting or no-difference."""
    first, second = winners[:rule["first"]], winners[:rule["second"]]
    if len(first) < rule["first"]:
        state = "no-difference" if trials >= rule["max_trials"] else "collecting"
        return state, winners.count("b"), len(winners)
    wins = first.count("b")
    if wins >= rule["adopt_first"] or wins <= rule["stop_first"]:
        return ("adopt" if wins >= rule["adopt_first"] else "stop"), wins, len(first)
    if len(second) < rule["second"]:
        return "continue", winners.count("b"), len(winners)
    wins = second.count("b")
    return ("adopt" if wins >= rule["adopt_second"] else "stop"), wins, len(second)
