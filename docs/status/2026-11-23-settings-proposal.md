# Proposed settings support, 23 Nov 2026

Status: design revised after the maintainer's quality-first feedback. No settings implementation, model call or adoption follows from this document. It is not a public test plan: no N, confirmatory seed or beacon round is set.

The build plan's P2 settings package requires per-arm settings, a verdict for quality at lower cost, and matching materials designed with the maintainer before implementation. The next source-native candidate for the selected host is [default-effort-first](../../claims/default-effort-first.md), from [Codex's Models guide](https://learn.chatgpt.com/docs/models).

## Smallest useful implementation

1. Add optional per-arm model and effort fields at `init`. Resolve the host defaults once and freeze explicit values; never inherit an ambient setting at run time. Preserve existing experiment fields and old-log interpretation. Keep vendor flags and supported settings in `presets.py`.
2. Record each arm's exact worker identity, model, effort, CLI version and command, plus the unchanged rendered-prompt hash. A pure settings comparison supplies the same prompt to both arms, with no rewriter or interview. Preserve confinement and subscription-only authentication.
3. Extend shared-control compatibility to the complete execution identity, including per-arm settings. Existing medium controls remain medium controls; they cannot stand in for low/default, Max, another model or multi-agent mode. Changed settings/materials use a new bench identity.
4. Retain persistent usage accounting, unknown-usage stops, five-minute worker timeouts and the six-million-token comparison ceiling. Report native multi-agent child consumption before any such arm is allowed; an incomplete meter blocks it. Do not implement multi-agent mode merely to finish the effort comparison.
5. Add meaningful offline tests for frozen settings, identical prompts, compatibility/reuse, old-format reading and fail-closed usage. Run both required Python suites. State compatibility and screen estimates before any subsequent live work.

## First candidate and quality/cost policy

Use the same pinned Codex model in both arms. Compare its explicitly resolved default effort with its highest supported single-agent effort. Verify supported settings from the installed CLI/catalog before freezing. The previous screen used explicit medium; the installed `gpt-6.1-sol` catalog gives low as its default. Neither model nor effort is silently upgraded when documentation changes.

Ordinary fully specified features provide partial ordinary-work support. Add a shared hard-work kind before interpreting the source's deeper-planning condition. Analyse ordinary and hard work apart; a missing private fact is not a hard reasoning problem.

The maintainer rejected a universal quality-loss allowance: coding should prioritize quality over usage, and other work should reflect its nature and stated priorities. The earlier ten/five-point alternatives and proposed 20% token cutoff are withdrawn. No settings experiment was frozen or run with them.

Use a quality-first decision for coding: required behavior, integrity and fidelity come before usage. Report quality and cost as separate dimensions by task kind, with uncertainty, rather than combining them into an arbitrary weighted score. Savings do not compensate for a known correctness regression. An uninformative quality comparison stays unresolved even when one arm is cheaper. A ten-task screen can find large regressions or flag a candidate, but cannot prove zero quality loss or establish equivalence.

The task's priority profile is fixed before execution from its stated use: correctness-critical coding, research whose factual accuracy and coverage matter, writing whose audience and fidelity matter, or explicitly time/budget-constrained work. Do not infer numerical preferences from a vague task label. A request that explicitly prioritizes a deadline or budget can justify a different decision profile, with the tradeoff stated; it does not change previously frozen comparisons. Per-kind confirmatory criteria still need a finite, interpretable quality target and sample size. Without a defensible non-inferiority margin, do not label a cheaper arm “as good”; report superiority, observed passes/failures and uncertainty instead. This preserves the existing protocol rather than silently setting its margin to zero.

Measure total execution tokens with cached input included, and report elapsed time separately. Dollar cost remains unknown when the CLI supplies no estimate. Treat comparison ceilings as limits on evaluation expenditure, separate from the priorities of future skill users.

### Research behind the revision

- [AI Agents That Matter](https://arxiv.org/abs/2407.01502), Kapoor et al., 2024: separates downstream-user evaluation from model ranking and argues for reporting accuracy with cost and protecting holdouts. This is methodological background, not evidence for a current prompting trick.
- [Beyond Leaderboard Ranks](https://arxiv.org/abs/2611.21515), Srinivasan and Menzies, 16 Nov 2026: its reanalysis finds most adjacent accuracy/cost-frontier differences statistically unresolved and substantial cost-accounting discrepancies. Its budget-aware selection procedure is not adopted here; unresolved differences are not interpreted as equivalence.
- [Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), Anthropic, 9 Jan 2026: distinguishes task outcomes from transcripts and recommends graders suited to the task, with human calibration where needed. Hidden checks cover only specified behavior; fidelity and usefulness need their own assessment.

The quality-first policy above is a project decision applying the maintainer's preference to these findings. It is not posted advice eligible for insertion into the skill.

## Matching materials

Build standard-library coding tasks that state all needed behavior, with hidden tests and independent reference/mutation checks. Candidate families are small routine refactors, dependency-aware cache invalidation, and an idempotent job-state machine with specified transition rules. Include ordinary and harder instances fixed by the design, not selected by which setting loses. These families are proposed for shared use across settings claims, not as tasks written for one trick.

For multi-agent advice, separately design tasks with genuinely independent pieces and tasks whose pieces depend on each other. Merely enlarging a feature is not proof of divisibility. For broader-exploration advice, preserve its multi-app information-discovery condition and develop suitable isolated app fixtures before claiming support.

The existing bank's pagination, health-route and CSV failures did not determine these proposed task families. Any new generator and render/settings contract starts a new experiment, with no retrospective tuning or reuse under a false identity.

## Release boundary

The most this first package can deliver is a valid development screen of the settings claim. A resulting skill note would be conditional, host-neutral and outside the copyable brief. It would suggest settings for the user to choose; it would not change the host's configuration. Fidelity, calibration, confirmatory tests, replication, a skill-form round and real-use acceptance remain separate gates.
