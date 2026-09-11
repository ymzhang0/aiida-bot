from pathlib import Path

from aiida_bot.diagnostics import diagnose, summarize
from aiida_bot.models import ProcessSnapshot
from aiida_bot.store import StateStore


def test_store_emits_only_state_changes(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    running = ProcessSnapshot(pk=12, label="PwCalculation", state="running")
    failed = ProcessSnapshot(pk=12, label="PwCalculation", state="finished", exit_status=401)
    assert store.observe(running) is None
    event = store.observe(failed)
    assert event and (event.old_state, event.new_state) == ("running", "finished")
    assert store.observe(failed) is None
    assert len(store.recent()) == 1


def test_oom_diagnosis_mentions_maxrss() -> None:
    snapshot = ProcessSnapshot(
        pk=31231, label="PwCalculation", state="finished", exit_status=401, scheduler_stderr="slurmstepd: error: Detected 1 oom-kill event"
    )
    assert diagnose(snapshot).kind == "oom"
    assert "MaxRSS" in summarize(snapshot)
