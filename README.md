# briefbench

Rewrite your prompts into better briefs for any AI model, and prove which rewrites actually help.

> **Status:** design stage. There's nothing to install yet. See [docs/design.md](docs/design.md).

## Why

Most prompts handed to AI agents are thin. Advice on writing better ones is everywhere, but little of it is tested, and independent tests found that several popular tricks do nothing reliable.

briefbench treats every prompting tip as a hypothesis:
1. It rewrites your prompt.
2. It runs both versions on the same task.
3. A judge from a different vendor picks the better result without knowing which prompt produced it.

Over time it keeps score of which techniques win on your own work.

## How it will work

1. **Rewrite.** It asks up to three questions: why you want this, what a stretch result looks like, and how to verify it. Then it turns your prompt into a brief you can paste into any chat or agent.
2. **A/B.** It runs your original and the rewrite side by side. A blind judge picks the better result.
3. **Scoreboard.** It tracks each technique's wins, losses and cost for each model, with a significance check.
4. **Adapt.** Techniques that keep winning stay, losers retire, and new tips start on trial.

It works with any model or harness: Claude, ChatGPT, Gemini, DeepSeek, local models and agent CLIs.

## Roadmap

| Stage | What you get | Status |
|---|---|---|
| 1. Rewrite | Better briefs, logged | Not started |
| 2. A/B | Blind comparisons | Not started |
| 3. Scoreboard | Evidence for each technique | Not started |
| 4. Adapt | A playbook that updates itself | Not started |
