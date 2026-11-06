# Security policy

## Reporting a vulnerability

Report vulnerabilities privately, through GitHub's private vulnerability reporting: open this repository's **Security** tab and click **Report a vulnerability**. Only you and the maintainer can see the report.

<!-- TODO(maintainer): enable private vulnerability reporting in the repository settings before publishing; the Report a vulnerability button appears only after that. -->

Please don't open a public issue, discussion or pull request about a vulnerability. If you can't find the button, open an issue that asks for a private channel, and leave out every detail of the problem.

Never paste API keys, tokens, passwords, or private prompts and outputs into a report. Show the problem with made-up values. If a real secret was exposed, revoke it first.

A useful report gives:

- the briefbench commit or version, and the skill version if the skill is involved
- your operating system, and the agent CLI and its version if they matter
- steps to reproduce, with made-up data
- what an attacker could do, as far as you know

Only the latest code on `main` is supported. There is one maintainer, so please allow time for a reply.

## What briefbench does on your machine

These notes help you judge whether something is a vulnerability.

- **It runs locally, as you.** `briefbench` starts agent CLIs, such as Claude Code (`claude -p`) and Codex (`codex exec`), on your machine with your own subscription logins. It has no server and no telemetry, and uploads nothing itself.
- **It removes API keys.** Each agent CLI starts without the API key variables in its environment, and without the variables that would send it to another endpoint or billing account. briefbench also replaces key values with `[redacted]` in what it prints and logs.
- **Its records stay local.** Experiments, trials and the log live under `~/.briefbench/`, or under `BRIEFBENCH_HOME` when that is set. The folder is created readable by you only.
- **The agent CLIs talk to their vendors.** They send your prompts, and the repo content they read, to their own vendor, as they do in normal use. The optional judge, when you allow it for a repo, sends diffs and check output to its vendor.
- **Trials run code with your permissions.** Your setup and check commands run in a shell, in each trial's git worktree. The worker can edit files in its worktree; every other call, such as the rewriter and the judge, gets read-only tools. The exact flags are in `src/briefbench/presets.py`. A worktree separates files, not processes, network access or your home folder.
- **The `brief` skill is text.** It is a Markdown file with no code. It runs inside your host, with that host's permissions.

## In scope

- briefbench passing an API key, or a variable that reroutes billing, to an agent CLI
- a key or token showing up in briefbench's output, log or records
- briefbench writing or deleting files outside its data folder and the repo you run it in, for example through a crafted experiment name or path
- records that other users on the machine can read
- skill instructions that lead a host to run commands or reveal data when it should only improve a prompt
- a workflow in this repository that exposes secrets or runs untrusted code with privileges

## Out of scope

- Vulnerabilities in Claude Code, Codex, or another agent CLI or host. Report them to their vendors.
- What an agent does within the permissions described above. Run trials only in repos, and with commands, that you trust.
- A brief that is poor but harmless. That is a skill behavior issue: open a public issue with a public example.
