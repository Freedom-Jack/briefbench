"""How many trials a public test needs, from its calibration on the plain prompt (docs/experiment-protocol.md, section
4, step 2, and section 8, "Planning a check-scored test"). Standard library and briefbench only.

    uv run python scripts/plan_trials.py --failed F/R --disagreed X/T [--harm-disagreed Y/U] [--gain 0.15] [--margin 0.10]

Where the trick should help: --failed is how many plain runs failed, of all its plain runs, and --disagreed how many
tasks had two plain runs that disagreed, of all its tasks. Where it could hurt: --harm-disagreed, the same. The script
checks that the plain prompt fails at least twice the smallest gain worth detecting (--gain), then gives N for each
kind of task by exact calculation: the first N from which the chance of finding the gain, or of showing "no loss over
--margin" when the trick does no harm, stays at --power or more. Then the runs the test will use.
"""
from __future__ import annotations

import argparse
import sys
from math import exp, lgamma, log, log1p

from briefbench.stats import interval, tango_interval

CAP = 1000                 # the most trials a fixed rule allows


def pmf(k: int, n: int, p: float) -> float:
    """P(Binomial(n, p) = k)."""
    if p <= 0 or p >= 1:
        return float(k == (0 if p <= 0 else n))
    return exp(lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1) + k * log(p) + (n - k) * log1p(-p))


def most_losses(alpha: float, top: int) -> list[int]:
    """For each number of decided pairs D up to top: the most losses L at which D - L wins, more than L, are
    significant under the exact two-sided sign test, computed as stats.sign_test does; -1 when no split is."""
    found = []
    for d in range(top + 1):
        most, below, term = -1, 0, 1                   # below: the sum of C(d, i) for i <= the losses tried
        for losses in range(d // 2 + 1):
            below += term
            if d - losses <= losses or 2 * below / 2 ** d > alpha:
                break
            most, term = losses, term * (d - losses) // (losses + 1)
        found.append(most)
    return found


def first_staying(chance, target: float, cap: int = CAP) -> int | None:
    """The first N from which chance(N) stays at target or more, looking well past where it first gets there."""
    last_below, reached = 0, None
    for n in range(1, cap + 1):
        if chance(n) < target:
            last_below = n
        elif reached is None:
            reached = n
        if reached and n >= max(1.3 * reached, reached + 30):
            return last_below + 1
    return None


def help_trials(d: float, gain: float, power: float, alpha: float) -> tuple[int | None, float]:
    """Trials where the trick should help, and the chance they give, when two plain runs disagree on a share d of
    tasks: q = d + gain of trials are decided, B wins with chance (q + gain) / 2, and D ~ Binomial(N, q)."""
    q = d + gain
    limits, win = most_losses(alpha, CAP), (q + gain) / (2 * q)
    tails = [sum(pmf(w, n, win) for w in range(n - most, n + 1)) if most >= 0 else 0.0
             for n, most in enumerate(limits)]
    chance = lambda n: sum(pmf(decided, n, q) * tails[decided] for decided in range(n + 1) if tails[decided])
    n = first_staying(chance, power)
    return n, chance(n) if n else 0.0


def harm_trials(d: float, margin: float, power: float, alpha: float) -> tuple[int | None, float]:
    """Trials where the trick could hurt, and the chance they give to show "no loss over margin": the lower end of
    Tango's interval above -margin, when the trick does no harm and two plain runs disagree on a share d of tasks."""
    def chance(n: int) -> float:
        total = 0.0
        for decided in range(n + 1):
            if (weight := pmf(decided, n, d)) < 1e-12:
                continue
            low, high = 0, decided + 1                  # the fewest wins for B that show the bound
            while low < high:
                middle = (low + high) // 2
                if tango_interval(middle, decided - middle, n, 1 - alpha)[0] > -margin:
                    high = middle
                else:
                    low = middle + 1
            total += weight * sum(pmf(w, decided, 0.5) for w in range(low, decided + 1))
        return total
    n = first_staying(chance, power)
    return n, chance(n) if n else 0.0


def count(text: str) -> tuple[int, int]:
    part, _, whole = text.partition("/")
    if not (part.isdigit() and whole.isdigit() and 0 <= int(part) <= int(whole) and int(whole) > 0):
        raise argparse.ArgumentTypeError("give a count as PART/WHOLE, such as 16/40")
    return int(part), int(whole)


def share(part: int, whole: int, noun: str) -> str:
    lo, hi = interval(part, whole)
    return f"{part} of {whole} {noun} ({part / whole:.0%}, 95% interval {lo:.0%} to {hi:.0%})"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--failed", type=count, required=True, help="plain runs failed, of plain runs, where the "
                                                                    "trick should help: F/R")
    parser.add_argument("--disagreed", type=count, required=True, help="tasks whose two plain runs disagreed, of "
                                                                       "tasks, where the trick should help: X/T")
    parser.add_argument("--harm-disagreed", type=count, help="the same where the trick could hurt: Y/U")
    parser.add_argument("--gain", type=float, default=0.15, help="the smallest gain in pass rate worth detecting "
                                                                 "(default 0.15)")
    parser.add_argument("--margin", type=float, default=0.10, help="the largest acceptable loss where the trick "
                                                                   "could hurt (default 0.10)")
    parser.add_argument("--power", type=float, default=0.80, help="the chance each kind should give (default 0.80)")
    parser.add_argument("--alpha", type=float, default=0.05, help="the two-sided level of the test (default 0.05)")
    args = parser.parse_args(argv)
    (failed, runs), (split, tasks) = args.failed, args.disagreed
    f, d = failed / runs, split / tasks
    print(f"Where the trick should help: the plain prompt failed {share(failed, runs, 'runs')}; its two runs "
          f"disagreed on {share(split, tasks, 'tasks')}.")
    if f < 2 * args.gain:
        print(f"No room on these materials: the plain prompt fails less than twice the smallest gain worth detecting "
              f"({2 * args.gain:.0%}), so no number of trials can be expected to show that gain. Make the tasks "
              "harder and calibrate again, with a new calibration seed.")
        return 1
    if d + args.gain > 1:
        print("The share of decided trials, d plus the gain, would be over 100%: check the counts.")
        return 2
    help_n, help_power = help_trials(d, args.gain, args.power, args.alpha)
    if not help_n:
        print(f"Over {CAP} trials would be needed where the trick should help, the most a fixed rule allows.")
        return 1
    print(f"  {help_n} trials give a chance of {help_power:.1%} to find a gain of {args.gain * 100:g} points (exact "
          f"two-sided sign test at {args.alpha:g}; q = d + gain = {d + args.gain:.2f} of trials decided).")
    total = help_n
    if args.harm_disagreed:
        split, tasks = args.harm_disagreed
        harm_n, harm_power = harm_trials(split / tasks, args.margin, args.power, args.alpha)
        if not harm_n:
            print(f"Over {CAP} trials would be needed where the trick could hurt.")
            return 1
        print(f"Where the trick could hurt: two plain runs disagreed on {share(split, tasks, 'tasks')}.")
        print(f"  {harm_n} trials give a chance of {harm_power:.1%} to show \"no loss over {args.margin * 100:g} "
              "points\" when the trick does no harm (the lower end of Tango's 95% interval).")
        total += harm_n
    print(f"In all: {total} trials, {2 * total} runs. Generate about 10% more tasks as reserves for reruns "
          f"({round(total * 1.1)}); they run only when a task's trial fails twice. A second test, after a win, uses "
          "as many again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
