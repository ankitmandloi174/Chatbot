"""Executes validated code in an isolated subprocess."""

import json
import logging
import subprocess
import sys
from pathlib import Path

from app.models.dataset import Dataset
from app.services.analysis.models import ExecutionResult

logger = logging.getLogger(__name__)
_RUNNER = Path(__file__).with_name("sandbox_runner.py")
_STDERR_TAIL = 1500


class ExecutionError(Exception):
    """Generated code failed at runtime (message is fed back to the LLM)."""


class SandboxExecutor:
    def __init__(self, timeout_seconds: int, memory_mb: int, max_rows: int) -> None:
        self._timeout = timeout_seconds
        self._memory_mb = memory_mb
        self._max_rows = max_rows

    def run(self, code: str, datasets: list[Dataset]) -> ExecutionResult:
        request = {
            "code": code,
            "datasets": [{"name": d.table_name, "path": d.parquet_path} for d in datasets],
            "max_rows": self._max_rows,
            "memory_mb": self._memory_mb,
            "cpu_seconds": self._timeout,
        }
        try:
            completed = subprocess.run(  # noqa: S603 - fixed interpreter and script path
                [sys.executable, "-I", str(_RUNNER)],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "2"},
                cwd="/",
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExecutionError(f"Execution timed out after {self._timeout}s; simplify or aggregate earlier") from exc

        try:
            outcome = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            logger.error("sandbox crashed", extra={"returncode": completed.returncode})
            tail = completed.stderr[-_STDERR_TAIL:]
            raise ExecutionError(f"Sandbox process failed (exit {completed.returncode}): {tail}") from exc

        if not outcome["ok"]:
            raise ExecutionError(outcome["error"])
        return ExecutionResult(
            result=outcome["result"], figure=outcome["figure"], stdout=outcome["stdout"]
        )
