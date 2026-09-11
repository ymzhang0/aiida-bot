from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import ProcessEvent, ProcessSnapshot


class StateStore:
    """Small local ledger: one current state per PK plus notification history."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS process_states (
                pk INTEGER PRIMARY KEY, state TEXT NOT NULL, exit_status INTEGER,
                snapshot TEXT NOT NULL
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, pk INTEGER NOT NULL, old_state TEXT NOT NULL,
                new_state TEXT NOT NULL, snapshot TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self.connection.commit()

    def observe(self, snapshot: ProcessSnapshot) -> ProcessEvent | None:
        row = self.connection.execute(
            "SELECT state, exit_status FROM process_states WHERE pk = ?", (snapshot.pk,)
        ).fetchone()
        payload = json.dumps(snapshot.as_dict(), ensure_ascii=False)
        changed = row is not None and (row[0], row[1]) != (snapshot.state, snapshot.exit_status)
        self.connection.execute(
            """INSERT INTO process_states (pk, state, exit_status, snapshot) VALUES (?, ?, ?, ?)
               ON CONFLICT(pk) DO UPDATE SET state=excluded.state, exit_status=excluded.exit_status,
               snapshot=excluded.snapshot""",
            (snapshot.pk, snapshot.state, snapshot.exit_status, payload),
        )
        if changed:
            self.connection.execute(
                "INSERT INTO events (pk, old_state, new_state, snapshot) VALUES (?, ?, ?, ?)",
                (snapshot.pk, row[0], snapshot.state, payload),
            )
        self.connection.commit()
        return ProcessEvent(snapshot.pk, str(row[0]), snapshot.state, snapshot) if changed else None

    def recent(self, limit: int = 20) -> list[tuple[ProcessEvent, str]]:
        rows = self.connection.execute(
            "SELECT pk, old_state, new_state, snapshot, created_at FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            (
                ProcessEvent(int(pk), old, new, ProcessSnapshot(**json.loads(snapshot))),
                created_at,
            )
            for pk, old, new, snapshot, created_at in rows
        ]

    def close(self) -> None:
        self.connection.close()
