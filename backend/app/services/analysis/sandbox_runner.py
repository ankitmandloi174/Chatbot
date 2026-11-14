"""Sandbox entry point. Runs in a separate, isolated Python subprocess.

Protocol: a JSON request on stdin ({"code", "datasets", "max_rows", "memory_mb",
"cpu_seconds"}); one JSON line on stdout with the outcome. This file is
self-contained on purpose (it runs with `python -I` and no access to `app`).

Isolation layers: AST validation (done by the parent), restricted builtins and
import hook, blocked sockets, address-space and CPU rlimits, and a scrubbed
environment (no API keys). This is PoC-grade isolation, not a hardened jail.
"""

import contextlib
import io
import json
import math
import resource
import socket
import sys
import traceback
from typing import Any

ALLOWED_IMPORTS = {"pandas", "numpy", "plotly", "math", "datetime", "statistics", "re", "collections"}
SAFE_BUILTIN_NAMES = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "int",
    "isinstance", "len", "list", "map", "max", "min", "pow", "print", "range", "repr",
    "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple", "zip",
    "Exception", "ValueError", "KeyError", "TypeError", "IndexError", "ZeroDivisionError",
    "True", "False", "None",
]


def _limit_resources(memory_mb: int, cpu_seconds: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 5))


def _block_network() -> None:
    def _blocked(*_: Any, **__: Any) -> None:
        raise PermissionError("network access is disabled in the sandbox")

    socket.socket = _blocked  # type: ignore[assignment, misc]
    socket.create_connection = _blocked  # type: ignore[assignment]


def _make_builtins() -> dict[str, Any]:
    import builtins

    safe = {name: getattr(builtins, name) for name in SAFE_BUILTIN_NAMES if hasattr(builtins, name)}

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.split(".")[0] not in ALLOWED_IMPORTS:
            raise ImportError(f"import of '{name}' is not allowed")
        return builtins.__import__(name, *args, **kwargs)

    safe["__import__"] = guarded_import
    return safe


def _json_safe(value: Any) -> Any:
    """Convert numpy/pandas scalars to JSON-safe Python values."""
    import numpy as np
    import pandas as pd

    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (np.generic,)):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _stringify_periods(frame: Any) -> Any:
    """Turn Period columns (e.g. from `dt.to_period("M")`) into strings.

    pandas' JSON writer cannot serialise Period values (it raises a misleading
    `OverflowError: Maximum recursion level reached`).
    """
    import pandas as pd

    for position in range(frame.shape[1]):
        if isinstance(frame.dtypes.iloc[position], pd.PeriodDtype):
            frame.isetitem(position, frame.iloc[:, position].astype(str))
    return frame


def _stringify_figure_periods(figure: Any) -> None:
    """Convert Period values inside Plotly traces to strings, which Plotly cannot encode."""
    import numpy as np
    import pandas as pd

    for trace in figure.data:
        for key, values in trace.to_plotly_json().items():
            if isinstance(values, np.ndarray) and values.dtype == object and len(values):
                if any(isinstance(v, pd.Period) for v in values[:1]):
                    trace[key] = [str(v) for v in values]


def _frame_payload(frame: Any, max_rows: int) -> dict[str, Any]:
    import pandas as pd

    if isinstance(frame, pd.Series):
        frame = frame.to_frame(name=str(frame.name) if frame.name is not None else "value")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = ["_".join(map(str, c)) for c in frame.columns]
    if not isinstance(frame.index, pd.RangeIndex):
        frame = frame.reset_index()
    frame = _stringify_periods(frame)
    total = len(frame)
    parsed = json.loads(frame.head(max_rows).to_json(orient="split", date_format="iso", date_unit="s"))
    return {
        "kind": "table",
        "columns": [str(c) for c in parsed["columns"]],
        "rows": parsed["data"],
        "total_rows": total,
        "truncated": total > max_rows,
    }


def _serialize_result(value: Any, max_rows: int) -> dict[str, Any]:
    import pandas as pd

    if isinstance(value, (pd.DataFrame, pd.Series)):
        return _frame_payload(value.copy(), max_rows)
    if isinstance(value, (dict, list, tuple)):
        return {"kind": "json", "value": json.loads(json.dumps(value, default=_json_safe))}
    return {"kind": "scalar", "value": _json_safe(value)}


def _user_error(exc: BaseException, code: str) -> str:
    """Format an error with the offending user-code line for LLM repair."""
    line_no = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == "<analysis>":
            line_no = frame.lineno
    message = f"{type(exc).__name__}: {exc}"
    if line_no:
        lines = code.splitlines()
        source = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
        message += f"\n(line {line_no}: {source})"
    return message[:2000]


def main() -> None:
    request = json.loads(sys.stdin.read())
    code: str = request["code"]
    _limit_resources(request["memory_mb"], request["cpu_seconds"])

    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import pyarrow.parquet  # noqa: F401 - preload: it imports `ssl`, which subclasses socket

    _block_network()
    dfs = {d["name"]: pd.read_parquet(d["path"]) for d in request["datasets"]}
    namespace: dict[str, Any] = {
        "__builtins__": _make_builtins(), "pd": pd, "np": np, "px": px, "go": go, "dfs": dfs, **dfs,
    }

    stdout_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer):
            exec(compile(code, "<analysis>", "exec"), namespace)  # noqa: S102 - sandboxed by design
        if "result" not in namespace:
            raise NameError("`result` was never assigned")
        figure = namespace.get("fig")
        if isinstance(figure, go.Figure):
            _stringify_figure_periods(figure)
        outcome: dict[str, Any] = {
            "ok": True,
            "result": _serialize_result(namespace["result"], request["max_rows"]),
            "figure": json.loads(figure.to_json()) if isinstance(figure, go.Figure) else None,
            "stdout": stdout_buffer.getvalue()[:2000],
        }
    except MemoryError:
        outcome = {"ok": False, "error": "MemoryError: analysis exceeded the memory limit; aggregate earlier"}
    except BaseException as exc:  # noqa: BLE001 - report everything back to the parent
        outcome = {"ok": False, "error": _user_error(exc, code)}

    sys.__stdout__.write(json.dumps(outcome))  # type: ignore[union-attr]


if __name__ == "__main__":
    main()
