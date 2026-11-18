"""The exact sign test, Clopper-Pearson intervals, the net-preference interval, Tango's interval for the difference,
an exact interval for a median and the two decision rules, in plain Python. Vendor-neutral."""
from __future__ import annotations

from math import comb, copysign, inf, sqrt
from statistics import NormalDist


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


def net_interval(wins: int, losses: int, trials: int, level: float = 0.95) -> tuple[float, float]:
    """A conservative interval for the net preference (wins - losses) / trials, where a tie counts zero
    (docs/experiment-protocol.md, section 8). It takes exact intervals, each at half the error, for the share of
    trials that were decided and for the win rate among them, then the extremes of share * (2 * rate - 1) over the
    four corners. By the union bound it covers at least `level`; with nothing decided the rate spans 0 to 1."""
    if trials == 0:
        return -1.0, 1.0
    each = 1 - (1 - level) / 2
    shares, rates = interval(wins + losses, trials, each), interval(wins, wins + losses, each)
    corners = [q * (2 * p - 1) for q in shares for p in rates]
    return min(corners), max(corners)


def tango_interval(wins: int, losses: int, trials: int, level: float = 0.95) -> tuple[float, float]:
    """Tango's score interval (1998) for the difference (wins - losses) / trials of paired trials, a tie counting zero:
    every d with |T(d)| <= z (docs/experiment-protocol.md, section 8). Unlike net_interval, it excludes zero whenever
    the exact sign test is significant at 1 - level."""
    if trials == 0:
        return -1.0, 1.0
    z, n = NormalDist().inv_cdf(1 - (1 - level) / 2), trials

    def t_stat(d: float) -> float:
        b, c = (2 * n - wins + losses) * d - wins - losses, -losses * d * (1 - d)
        a_wins = (-b + sqrt(max(b * b - 8 * n * c, 0.0))) / (4 * n)    # A's chance to win a trial, were the difference d
        top, spread = wins - losses - n * d, n * (2 * a_wins + d * (1 - d))
        return 0.0 if top == 0 else top / sqrt(spread) if spread > 0 else copysign(inf, top)

    def bisect(inside: float, outside: float, keep) -> float:
        for _ in range(60):
            middle = (inside + outside) / 2
            inside, outside = (middle, outside) if keep(middle) else (inside, middle)
        return (inside + outside) / 2

    estimate = (wins - losses) / n
    lower = -1.0 if t_stat(-1.0) <= z else bisect(estimate, -1.0, lambda d: t_stat(d) <= z)
    upper = 1.0 if t_stat(1.0) >= -z else bisect(estimate, 1.0, lambda d: t_stat(d) >= -z)
    return lower, upper


def median_interval(values: list[float], level: float = 0.95) -> tuple[float, float] | None:
    """An exact interval for the median from order statistics, with no assumption about the shape of the data: from
    the k-th smallest value to the k-th largest, where k is the largest whole number with P(Binomial(n, 1/2) <= k - 1)
    at most (1 - level) / 2. It covers the median at least `level` of the time. None below 6 values, where no k is."""
    values, n = sorted(values), len(values)
    k, below = 0, 0                                  # below: the sum of C(n, i) for i < k
    while k < n and (below + comb(n, k)) / 2 ** n <= (1 - level) / 2:
        below, k = below + comb(n, k), k + 1
    return (values[k - 1], values[n - k]) if k else None


def decide(winners: list[str], trials: int, rule: dict) -> tuple[str, int, int]:
    """The two-step rule on B's wins (docs/design.md, "Decision rules"). winners: "a" or "b" for each decided pair,
    in the order they were run; trials counts ties too. Returns (state, B's wins, pairs) for the pairs the rule
    looked at. state is adopt, stop, continue, collecting or no-difference."""
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


def decide_fixed(wins: int, losses: int, trials: int, rule: dict) -> str:
    """The fixed-sample rule: one two-sided sign test once exactly rule["trials"] trials are in, never before
    (docs/design.md, "Decision rules"). The caller passes the counts of the first rule["trials"] trials only.
    Returns collecting, benefit, below-threshold (B is significantly better, but its net preference is under the
    frozen threshold), harm or no-difference."""
    if trials < rule["trials"]:
        return "collecting"
    if sign_test(wins, losses) > rule["alpha"]:
        return "no-difference"
    if losses > wins:
        return "harm"
    return "benefit" if (wins - losses) / trials >= rule["net_min"] else "below-threshold"
