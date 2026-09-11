from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path

from .aiida import AiiDACollector
from .diagnostics import summarize
from .models import ProcessSnapshot
from .notify import desktop_notification
from .store import StateStore


def _default_db() -> Path:
    root = Path.home() / ("Library/Application Support" if os.uname().sysname == "Darwin" else ".local/share")
    return root / "aiida-bot" / "state.sqlite3"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aiida-bot", description="Provenance-aware AiiDA watcher")
    parser.add_argument("--profile", help="AiiDA profile (default: current profile)")
    parser.add_argument("--state-db", type=Path, default=_default_db())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("profiles", help="list configured AiiDA profiles")
    commands.add_parser("status", help="show current process-state counts")
    recent = commands.add_parser("recent", help="show detected state transitions")
    recent.add_argument("--limit", type=int, default=20)
    why = commands.add_parser("why", help="inspect and diagnose one process")
    why.add_argument("pk", type=int)
    watch = commands.add_parser("watch", help="continuously watch all recent processes or one PK")
    watch.add_argument("pk", type=int, nargs="?")
    watch.add_argument("--interval", type=float, default=30.0)
    watch.add_argument("--limit", type=int, default=200)
    watch.add_argument("--notify", action="store_true", help="send local desktop notifications")
    return parser


def _print_snapshot(snapshot: ProcessSnapshot) -> None:
    print(json.dumps(snapshot.as_dict(), ensure_ascii=False, indent=2))
    print(summarize(snapshot))


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    store = StateStore(args.state_db)
    collector = AiiDACollector(args.profile)
    try:
        if args.command == "profiles":
            from aiida.manage.configuration import get_config

            for name in get_config().profile_names:
                print(name)
            return
        if args.command == "recent":
            for event, created_at in store.recent(args.limit):
                print(f"{created_at}  #{event.pk}: {event.old_state} → {event.new_state}")
                print(summarize(event.snapshot))
            return
        try:
            collector.load_profile()
        except Exception as error:
            from aiida.common.exceptions import ProfileConfigurationError

            if not isinstance(error, ProfileConfigurationError):
                raise
            from aiida.manage.configuration import get_config

            names = ", ".join(get_config().profile_names) or "(none)"
            raise SystemExit(
                f"Unknown AiiDA profile {args.profile!r}. Available profiles: {names}. "
                "Run `aiida-bot profiles` or omit --profile to use AiiDA's default."
            ) from error
        if args.command == "why":
            _print_snapshot(collector.get(args.pk))
            return
        if args.command == "status":
            snapshots = collector.recent()
            counts = Counter(snapshot.state for snapshot in snapshots)
            print(json.dumps({"profile": args.profile, "processes": len(snapshots), "states": dict(counts)}, ensure_ascii=False))
            return
        _watch(collector, store, args)
    finally:
        store.close()


def _watch(collector: AiiDACollector, store: StateStore, args: argparse.Namespace) -> None:
    print(f"Watching AiiDA {'process ' + str(args.pk) if args.pk else 'processes'} every {args.interval:g}s. Ctrl-C to stop.")
    while True:
        snapshots = [collector.get(args.pk)] if args.pk else collector.recent(args.limit)
        for snapshot in snapshots:
            event = store.observe(snapshot)
            if event is None:
                continue
            message = summarize(snapshot)
            print(message, flush=True)
            if args.notify:
                desktop_notification("AiiDA Bot", message)
        time.sleep(max(args.interval, 1.0))


if __name__ == "__main__":
    main()
