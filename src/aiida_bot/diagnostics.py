from __future__ import annotations

from dataclasses import dataclass

from .models import ProcessSnapshot


@dataclass(frozen=True)
class Diagnosis:
    kind: str
    emoji: str
    explanation: str
    advice: str


def diagnose(snapshot: ProcessSnapshot) -> Diagnosis:
    text = "\n".join(
        value or ""
        for value in (
            snapshot.scheduler_state,
            snapshot.scheduler_stderr,
            snapshot.scheduler_stdout,
            snapshot.output_tail,
            snapshot.report_tail,
            snapshot.exit_message,
        )
    ).upper()
    if any(token in text for token in ("OUT_OF_MEMORY", "OUT OF MEMORY", "OOM", "MEMORY LIMIT", "KILLED BY OOM")):
        return Diagnosis("oom", "💀", "看起来是内存不足，不是数值问题。", "检查 sacct 的 MaxRSS；增加内存或减少每节点 MPI ranks。")
    if any(token in text for token in ("TIME LIMIT", "WALLTIME", "DUE TO TIME LIMIT")):
        return Diagnosis("walltime", "⌛", "作业碰到了 walltime 限制。", "增加 max_wallclock_seconds，或把工作流拆成更小的步骤。")
    if any(token in text for token in ("CONVERGENCE NOT ACHIEVED", "SCF NOT CONVERGED", "TOO MANY ITERATIONS")):
        return Diagnosis("convergence", "📉", "这是电子结构收敛问题。", "检查 mixing、电子温度、k 点和初始磁矩；通常不需要直接加内存。")
    if "MPI" in text or "MPIRUN" in text:
        return Diagnosis("mpi", "🔥", "MPI 运行时异常终止。", "核对 MPI 模块、进程数和每节点资源分布。")
    if snapshot.state.lower() == "killed":
        return Diagnosis("killed", "🛑", "进程被主动终止。", "检查是谁发出了 kill 请求及 scheduler 记录。")
    if snapshot.state.lower() == "finished" and (snapshot.exit_status in (None, 0)):
        return Diagnosis("success", "🎉", "任务正常完成。", "结果已经可供后续 provenance 节点使用。")
    return Diagnosis("unknown", "🔥", "AiiDA 进程没有正常结束。", "查看 scheduler stderr、AiiDA report 和最后的输出内容。")


def summarize(snapshot: ProcessSnapshot) -> str:
    result = diagnose(snapshot)
    identity = f"{snapshot.label}<{snapshot.pk}>"
    parent = f"，属于 {snapshot.root_workchain}" if snapshot.root_workchain else ""
    phase = f"，当前阶段：{snapshot.phase}" if snapshot.phase else ""
    exit_note = f" exit status {snapshot.exit_status}" if snapshot.exit_status not in (None, 0) else ""
    return f"{result.emoji} {identity} {snapshot.state}{exit_note}{parent}{phase}。{result.explanation}建议：{result.advice}"
