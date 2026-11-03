---
name: brief
description: Rewrites a rough prompt into one clear brief for an AI agent or model, after asking at most three short questions the prompt leaves open (why the user wants it, how the result will be checked, and an optional stretch result). Use when the user types /brief or $brief, asks for "a brief", or asks to improve, sharpen or rewrite a prompt before handing it to an agent. It writes the brief only; it does not do the task.
license: MIT
metadata:
  version: "0.1.0"
---

# Brief

Turn the user's prompt into one brief that another agent or model can act on well. You write the brief; you don't do the task, even when it is short or easy.

## Steps

1. **Find the prompt.** With `/brief <text>`, the text is the prompt. With `/brief` alone, it is the user's last message before it. If there is no prompt, ask for one and stop.
2. **Read what the prompt points to, and nothing more:** files, links or earlier messages it names or clearly refers to. Use them to understand the task, to answer questions yourself instead of asking, and to keep its specifics exact. Don't explore beyond them.
3. **Ask what is left open, in one message.** There are three possible questions. Ask only those that the prompt, what it points to and the conversation don't already answer:
   - Why do you want this? What is the result for, and what happens next with it?
   - How will the result be checked by something other than the model: a test, a command, data, or a person?
   - Optional: what would a stretch result look like, beyond what you strictly need? Ask this one only when the task has room to go further than what is needed.

   Word each question to fit the task. Use the host's question tool if it has one, with short answer options drawn from what you read plus free text; otherwise ask in plain text. Say that any question can be skipped. Ask nothing, and write the brief from what you have, when all three are answered, when the user asks you not to ask, or when no one can answer, as in a headless run.
4. **Write the brief**, following the rules and techniques below, with whatever answers you got.
5. **Return it** in one fenced code block, so it copies cleanly. If the brief itself contains a code fence, make the outer fence longer than any run of backticks inside it. Put nothing before the block but, at most, one short line. After it, offer to run the brief.

## Rules for the brief

- Rewrite the whole prompt into one coherent brief. Reorder and tighten freely, but keep every request in it.
- Keep the requester's specifics word for word: names, numbers, paths, commands, URLs and quoted text.
- Add nothing the requester didn't say or point to: no goals, reasons, requirements, numbers, files, tools, checks or limits of your own. Leave out a skipped question; never guess its answer.
- Say what is wanted and why, not how: no plan, design or steps of your own for doing the task. Point to files, links and messages instead of pasting them in; the agent can read them.
- Write to the agent as "you", in plain, short sentences or short lists, in the language of the prompt.
- No persona or role ("You are an expert…"), praise, rewards, threats, urgency or capitals for emphasis. No advice that would fit any task, such as "be thorough" or "double-check your work".
- Keep only the parts that have content: no empty labels, no "N/A", no "not stated". A short prompt with little to add stays short.

## Techniques

Use each technique only where the prompt, what it points to or the answers give it content. Use short labels or lists where they help the reader; skip headings unless the brief is long.

1. **Background and why.** Say what the result is for and what happens next with it, from the answer to the why question or a purpose the prompt states. Include background from that answer that changes how the work is done, such as who the result is for or what went wrong before. If the prompt names raw material, such as files, logs, data or links, tell the agent to start from that material itself rather than from summaries of it. Leave this out when no purpose was given, or when the prompt already states it plainly.
2. **Outcome, with a stretch target.** State the required result as an end state rather than an activity, but only when the requester describes a result beyond the literal task; don't restate the task. Add a stretch target only when the requester gave one: in their own words and numbers, marked as an aim and not a requirement, with a request to report how close the work came. Never make one up.
3. **Verification outside the model.** Name the checks the requester gave, each exactly as written: tests or commands to run, figures to reproduce from raw data, predictions to test against data the model hasn't seen, or a person who will review the result. Ask the agent to run each check it can run itself and to report the actual results, failures included. Add no checks of your own, and never ask the agent to review, grade or double-check its own work.
4. **Definition of done.** List what must be true for the work to count as finished, and what to hand back, such as a pull request, a file or a short report. Use only what the requester said or directly implied, and write each item so it can be seen to be true or false. Leave out the stretch target. Skip this when the list would only repeat the prompt, the outcome or the checks.
5. **Constraints and non-goals.** List the limits the work must respect, in the requester's words: what must not change, tools or approaches to use or avoid, compatibility to keep, and any budget, deadline or scope limit. Gather limits mentioned in passing anywhere in the prompt or the answers. Mark anything the requester ruled out as "Non-goal:". Add no limits of your own, not even generic ones such as "keep it simple".

## Example

The prompt: "the login test keeps failing randomly, fix it. tests/test_auth.py". Answers: why, "CI fails about one run in five and people just re-run it"; check, "pytest tests/test_auth.py --count=50 passes locally"; stretch, skipped.

````text
Fix the login test in tests/test_auth.py, which fails at random.

Why: CI fails on it about one run in five, and people just re-run it.

Check: run `pytest tests/test_auth.py --count=50` locally, and report the actual result, failures included.
````

There is no stretch target, because the stretch question was skipped. There is no "Done when" list, because it would only repeat the check.
