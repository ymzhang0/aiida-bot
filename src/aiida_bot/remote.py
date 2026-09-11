"""SSH-friendly server/client pair for aiida-bot.

The server writes newline-delimited JSON to stdout only.  SSH supplies the
transport, encryption, and authentication; the client turns events into local
desktop notifications.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable, TextIO

from .aiida import AiiDACollector
from .diagnostics import diagnose, summarize
from .models import ProcessSnapshot
from .notify import desktop_notification
from .store import StateStore


def avatar(snapshot: ProcessSnapshot) -> str:
    """The bot's compact visual identity, usable in terminals and notifications."""
    if snapshot.state.lower() in {"running", "waiting", "created"}:
        return "🐇"
    return diagnose(snapshot).emoji


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m aiida_bot.remote")
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("server", help="run beside the AiiDA profile and emit JSON events")
    server.add_argument("--profile")
    server.add_argument("--state-db", type=Path, default=Path(".aiida-bot-state.sqlite3"))
    server.add_argument("--interval", type=float, default=30.0)
    server.add_argument("--limit", type=int, default=200)
    server.add_argument("pk", type=int, nargs="?")
    client = commands.add_parser("client", help="read server JSON events from stdin and notify locally")
    client.add_argument("--no-notify", action="store_true")
    return parser


def event_payload(snapshot: ProcessSnapshot, old_state: str, new_state: str) -> dict[str, Any]:
    return {
        "type": "aiida.process.transition",
        "pk": snapshot.pk,
        "old_state": old_state,
        "new_state": new_state,
        "avatar": avatar(snapshot),
        "message": summarize(snapshot),
        "snapshot": snapshot.as_dict(),
    }


def serve(args: argparse.Namespace, output: TextIO = sys.stdout) -> None:
    collector = AiiDACollector(args.profile)
    store = StateStore(args.state_db)
    try:
        collector.load_profile()
        while True:
            snapshots = [collector.get(args.pk)] if args.pk else collector.recent(args.limit)
            for snapshot in snapshots:
                event = store.observe(snapshot)
                if event is not None:
                    print(json.dumps(event_payload(snapshot, event.old_state, event.new_state), ensure_ascii=False), file=output, flush=True)
            time.sleep(max(args.interval, 1.0))
    finally:
        store.close()


def relay(lines: Iterable[str], *, notify: bool = True, output: TextIO = sys.stdout) -> int:
    """Consume a server stream. Malformed lines stay visible but never stop it."""
    delivered = 0
    for line in lines:
        try:
            event = json.loads(line)
            snapshot = ProcessSnapshot(**event["snapshot"])
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        message = str(event.get("message") or summarize(snapshot))
        print(message, file=output, flush=True)
        if notify:
            desktop_notification(f"AiiDA Bot {event.get('avatar') or avatar(snapshot)}", message)
        delivered += 1
    return delivered


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "server":
        serve(args)
    else:
        relay(sys.stdin, notify=not args.no_notify)


if __name__ == "__main__":
    main()
