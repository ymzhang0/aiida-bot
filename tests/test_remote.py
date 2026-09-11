import io
import json

from aiida_bot.models import ProcessSnapshot
from aiida_bot.remote import event_payload, relay


def test_relay_reads_one_server_event() -> None:
    snapshot = ProcessSnapshot(pk=7, label="PwCalculation", state="finished", exit_status=0)
    stream = io.StringIO(json.dumps(event_payload(snapshot, "running", "finished")) + "\n")
    output = io.StringIO()
    assert relay(stream, notify=False, output=output) == 1
    assert "🎉" in output.getvalue()
