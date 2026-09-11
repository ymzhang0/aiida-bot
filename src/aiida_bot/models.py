from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProcessSnapshot:
    pk: int
    label: str
    state: str
    exit_status: int | None = None
    exit_message: str | None = None
    process_type: str | None = None
    mtime: str | None = None
    parent: str | None = None
    root_workchain: str | None = None
    phase: str | None = None
    scheduler_state: str | None = None
    scheduler_stdout: str | None = None
    scheduler_stderr: str | None = None
    output_tail: str | None = None
    report_tail: str | None = None
    max_memory_kb: int | None = None
    walltime_seconds: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessEvent:
    pk: int
    old_state: str
    new_state: str
    snapshot: ProcessSnapshot


TERMINAL_STATES = frozenset({"finished", "excepted", "killed"})


def is_terminal(state: str) -> bool:
    return state.lower() in TERMINAL_STATES
