from __future__ import annotations

from contextlib import suppress
from typing import Any

from .models import ProcessSnapshot


def _text(value: Any, limit: int = 2400) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned[-limit:] if cleaned else None


def _state(node: Any) -> str:
    value = getattr(node, "process_state", None)
    return str(getattr(value, "value", value) or "unknown")


class AiiDACollector:
    def __init__(self, profile: str | None = None) -> None:
        self.profile = profile
        self.orm: Any | None = None

    def load_profile(self) -> None:
        from aiida import load_profile, orm

        load_profile(self.profile) if self.profile else load_profile()
        self.orm = orm

    def recent(self, limit: int = 200) -> list[ProcessSnapshot]:
        if self.orm is None:
            self.load_profile()
        from aiida.orm import QueryBuilder

        query = QueryBuilder().append(self.orm.ProcessNode, project=["id"], tag="process", subclassing=True)
        query.order_by({"process": {"mtime": "desc"}}).limit(limit)
        return [self.snapshot(self.orm.load_node(pk)) for (pk,) in query.all()]

    def get(self, pk: int) -> ProcessSnapshot:
        if self.orm is None:
            self.load_profile()
        return self.snapshot(self.orm.load_node(pk))

    def snapshot(self, node: Any) -> ProcessSnapshot:
        orm = self.orm
        assert orm is not None
        parent = getattr(node, "caller", None)
        root = parent
        while getattr(root, "caller", None) is not None:
            root = root.caller
        attrs = getattr(node.base, "attributes", None)
        metadata_inputs = getattr(attrs, "all", {}).get("metadata_inputs", {}) if attrs else {}
        metadata = metadata_inputs.get("metadata", {}) if isinstance(metadata_inputs, dict) else {}
        phase = metadata.get("call_link_label") if isinstance(metadata, dict) else None
        reports = self._reports(node)
        details: dict[str, Any] = {}
        stdout = stderr = output = scheduler_state = None
        memory = walltime = None
        if isinstance(node, orm.CalcJobNode):
            with suppress(Exception):
                stdout = _text(node.get_scheduler_stdout())
            with suppress(Exception):
                stderr = _text(node.get_scheduler_stderr())
            with suppress(Exception):
                scheduler_state = _text(node.get_scheduler_state())
            with suppress(Exception):
                memory = node.get_option("max_memory_kb")
            with suppress(Exception):
                walltime = node.get_option("max_wallclock_seconds")
            output = self._output_tail(node)
            with suppress(Exception):
                details["remote_workdir"] = node.get_remote_workdir()
        return ProcessSnapshot(
            pk=int(node.pk),
            label=str(getattr(node, "process_label", None) or node.label or type(node).__name__),
            process_type=_text(getattr(node, "process_type", None)),
            state=_state(node),
            exit_status=getattr(node, "exit_status", None),
            exit_message=_text(getattr(node, "exit_message", None)),
            mtime=node.mtime.isoformat() if getattr(node, "mtime", None) else None,
            parent=self._name(parent),
            root_workchain=self._name(root) if parent else None,
            phase=_text(phase, 240),
            scheduler_state=scheduler_state,
            scheduler_stdout=stdout,
            scheduler_stderr=stderr,
            output_tail=output,
            report_tail=reports,
            max_memory_kb=int(memory) if isinstance(memory, (int, float)) else None,
            walltime_seconds=int(walltime) if isinstance(walltime, (int, float)) else None,
            details=details,
        )

    @staticmethod
    def _name(node: Any | None) -> str | None:
        if node is None:
            return None
        return f"{getattr(node, 'process_label', None) or node.label or type(node).__name__}<{node.pk}>"

    def _reports(self, node: Any) -> str | None:
        from aiida.orm import QueryBuilder

        for key in ("dbnode_id", "objpk"):
            with suppress(Exception):
                rows = QueryBuilder().append(self.orm.Log, filters={key: int(node.pk)}, project=["message"], tag="log").order_by(
                    {"log": {"time": "asc"}}
                ).all()
                if rows:
                    return _text("\n".join(str(message) for (message,) in rows))
        return None

    @staticmethod
    def _output_tail(node: Any) -> str | None:
        with suppress(Exception):
            retrieved = node.outputs.retrieved
            filename = node.get_option("output_filename")
            return _text(retrieved.base.repository.get_object_content(filename))
        return None
