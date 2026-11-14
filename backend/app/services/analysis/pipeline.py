"""Plan -> generate -> validate -> execute loop with LLM-assisted repair."""

import logging
import time

from app.models.dataset import Dataset
from app.services.analysis.code_generator import CodeGenerator
from app.services.analysis.code_validator import CodeValidationError, validate_code
from app.services.analysis.models import AnalysisOutcome, AttemptLog
from app.services.analysis.planner import AnalysisPlanner
from app.services.analysis.sandbox import ExecutionError, SandboxExecutor

logger = logging.getLogger(__name__)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


class AnalysisPipeline:
    def __init__(
        self,
        planner: AnalysisPlanner,
        generator: CodeGenerator,
        executor: SandboxExecutor,
        max_retries: int,
    ) -> None:
        self._planner = planner
        self._generator = generator
        self._executor = executor
        self._max_retries = max_retries

    def run(
        self,
        question: str,
        datasets: list[Dataset],
        schema_text: str,
        history_text: str,
    ) -> AnalysisOutcome:
        """Run the analysis. Failures are returned (not raised) so the API can report them."""
        started = time.perf_counter()
        plan = self._planner.plan(question, schema_text, history_text)
        planning_ms = _elapsed_ms(started)
        needed = self._datasets_for_plan(plan.datasets, datasets)
        loaded = [d.table_name for d in needed]

        code, error = "", None
        log: list[AttemptLog] = []
        total_attempts = self._max_retries + 1
        for attempt in range(1, total_attempts + 1):
            started = time.perf_counter()
            code = self._generator.generate(
                question, plan, schema_text, history_text,
                failed_code=code if error else None, error=error,
            )
            try:
                validate_code(code)
            except CodeValidationError as exc:
                error = str(exc)
                log.append(AttemptLog(attempt=attempt, code=code, validation="failed",
                                      execution="skipped", error=error, duration_ms=_elapsed_ms(started)))
                logger.warning("analysis attempt failed", extra={"attempt": attempt, "error": error})
                continue
            try:
                execution = self._executor.run(code, needed)
            except ExecutionError as exc:
                error = str(exc)
                log.append(AttemptLog(attempt=attempt, code=code, validation="passed",
                                      execution="failed", error=error, duration_ms=_elapsed_ms(started)))
                logger.warning("analysis attempt failed", extra={"attempt": attempt, "error": error})
                continue
            log.append(AttemptLog(attempt=attempt, code=code, validation="passed",
                                  execution="passed", duration_ms=_elapsed_ms(started)))
            return AnalysisOutcome(
                plan=plan, code=code, attempts=attempt, execution=execution,
                attempt_log=log, planning_ms=planning_ms, loaded_datasets=loaded,
            )

        return AnalysisOutcome(
            plan=plan, code=code, attempts=total_attempts, error=error,
            attempt_log=log, planning_ms=planning_ms, loaded_datasets=loaded,
        )

    @staticmethod
    def _datasets_for_plan(names: list[str], datasets: list[Dataset]) -> list[Dataset]:
        """Load only datasets the plan names; fall back to all if the plan is empty/unknown."""
        chosen = [d for d in datasets if d.table_name in set(names)]
        return chosen or datasets
