# AiiDA Bot

`aiida-bot` watches AiiDA processes through the ORM, remembers transitions in a
small SQLite file, and produces provenance-aware diagnoses. It is deliberately
separate from AiiDA's daemon: a bad notification or missing desktop session can
never interrupt a calculation.

## Install

Install it in the Python environment that owns the target AiiDA profile:

```bash
cd aiida-bot
uv sync --extra dev
uv run aiida-bot profiles
uv run aiida-bot status  # uses AiiDA's default profile
```

## Use

```bash
# First run records a baseline; later changes are emitted once.
uv run aiida-bot watch --notify

# Focus on a workflow or calculation.
uv run aiida-bot --profile <your-real-profile-name> watch 31200 --interval 15

# Inspect a failure, including AiiDA reports and scheduler output when present.
uv run aiida-bot --profile <your-real-profile-name> why 31231

# Show the persisted notification history.
uv run aiida-bot recent
```

`watch` has no LLM dependency. It applies deterministic OOM, walltime,
convergence, MPI, and killed-process diagnostics first, then emits a concise
Chinese summary. This keeps reports useful when the network or an AI provider
is unavailable. An MCP tool or an LLM adapter can consume the JSON from
`aiida-bot why PK` later without coupling that service to the watcher.

## Deployment

Run the watcher next to the AiiDA profile (normally the login/server host).
`--notify` is for a local desktop session; a remote server should forward the
printed event to Slack, email, or a small local client instead.

`retry` is intentionally not implemented: automatic replay is workflow-plugin
specific and should require an explicit, reviewable recovery policy.
