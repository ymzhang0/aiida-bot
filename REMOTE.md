# Remote server and Mac client

Install the same `aiida-bot` checkout in the Python environment that owns the
AiiDA profile on the remote login host. The server keeps its own SQLite state
file there and writes only newline-delimited JSON to standard output.

On the remote host:

```bash
cd ~/aiida-bot
uv run python -m aiida_bot.remote server --profile production --interval 30
```

On the Mac, tunnel that stream over SSH and turn every event into a native
notification:

```bash
ssh user@login-host 'cd ~/aiida-bot && uv run python -m aiida_bot.remote server --profile production' \
  | uv run --project /path/to/aiida-bot python -m aiida_bot.remote client
```

The first server run records the current state and remains quiet. Later state
transitions emit one event each. SSH is the only network transport: no AiiDA
database port or new web service is exposed.

The client includes the bot avatar in its notification title:

- `🐇` running / waiting
- `🎉` completed successfully
- `🔥` failed
- `💀` likely OOM
