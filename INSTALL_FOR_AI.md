# ReproAI — install instructions for an AI assistant

ReproAI is an author-facing pre-diagnose plugin for replication packages (Stata / R / Python),
backed by a small Python engine. **This file is the install procedure for an AI assistant to run.**
Execute it deterministically: detect your host, run only that host's branch, then verify.

## Prerequisites

- **Python 3.10+** on PATH (`python3 --version`).
- **One host**: Claude Code **or** OpenAI Codex CLI.
- A shell you can run commands in.

## Step 1 — detect the host

Determine which host you are running inside, then follow ONLY that branch:

- **Claude Code** — you have `/plugin` slash commands. → use Branch A.
- **OpenAI Codex CLI** — you do not have `/plugin`; you install via the user's shell. → use Branch B.

If you cannot tell, ask the user which host this is. Do not run both branches.

## Step 2A — install in Claude Code

Run the first two commands **inside Claude Code** (slash commands), and the `pip` command in
**the user's shell**:

```
/plugin marketplace add leoyyang/reproai
/plugin install reproai@reproai                                          # plugin@marketplace
pip install "git+https://github.com/leoyyang/reproai#subdirectory=core"  # the engine, on PATH
```

- `/plugin marketplace add …` — runs in Claude Code. Success: the `reproai` marketplace is registered.
- `/plugin install reproai@reproai` — runs in Claude Code. Success: the `/reproai:*` commands appear.
- `pip install …` — runs in the user's shell. Success: pip reports the `reproai` engine installed.

## Step 2B — install in OpenAI Codex CLI

Run all of these in **the user's shell**:

```
git clone https://github.com/leoyyang/reproai
cd reproai
./codex-plugin/install.sh   # links the reproai skills into ~/.agents/skills
pip install -e core         # put the reproai engine on PATH
```

- `git clone …` — shell. Success: a `reproai/` directory exists.
- `cd reproai` — shell. Success: you are in the repo root.
- `./codex-plugin/install.sh` — shell. Success: it prints `linked skill: reproai-*` lines.
- `pip install -e core` — shell. Success: pip reports the `reproai` engine installed (editable).

## Step 3 — verify

In **the user's shell**, confirm the engine is on PATH and importable:

```
reproai --version                                    # prints: reproai <version>
python3 -c "import line1_core; print('ok')"          # prints: ok
```

Then confirm the host has the commands:

- **Claude Code**: the `/reproai:check` command is listed/available (e.g. type `/reproai:` to see it).
- **Codex**: the `reproai-check` skill is available (linked under `~/.agents/skills/`).

If `reproai --version` is not found, the engine `pip install` step did not complete — rerun it.

## Update

Refresh **both** the plugin (commands) and the engine (rules + venue profiles).

**Claude Code** — first three inside Claude Code, last in the user's shell:

```
/plugin marketplace update reproai
/plugin update reproai          # latest commands
/reload-plugins
pip install -U "git+https://github.com/leoyyang/reproai#subdirectory=core"  # latest rules + venues
```

**OpenAI Codex CLI** — in the user's shell (pull the repo, then):

```
reproai/codex-plugin/install.sh   # relink skills
pip install -U -e reproai/core
```

---

Human install lives at https://reproai.org (Install section) and the README.
