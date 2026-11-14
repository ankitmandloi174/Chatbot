"""Static (AST) validation of LLM-generated code before it is executed."""

import ast

FORBIDDEN_NAMES = {
    "__import__", "eval", "exec", "compile", "open", "input", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "breakpoint", "exit", "quit", "help", "memoryview",
}
FORBIDDEN_ATTRIBUTES = {
    "io", "os", "sys", "subprocess", "system", "popen", "pickle", "ctypes", "builtins",
    "importlib", "to_csv", "to_excel", "to_parquet", "to_pickle", "to_sql", "to_hdf",
    "to_feather", "to_stata", "to_orc", "write_html", "write_image", "write_json", "show",
}
FORBIDDEN_ATTRIBUTE_PREFIXES = ("read_", "__")


class CodeValidationError(Exception):
    """Raised when generated code violates the sandbox policy."""


def validate_code(code: str) -> None:
    """Reject code that is unparsable, unsafe, or does not define `result`."""
    try:
        tree = ast.parse(code, filename="<analysis>")
    except SyntaxError as exc:
        raise CodeValidationError(f"SyntaxError on line {exc.lineno}: {exc.msg}") from exc

    assigns_result = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise CodeValidationError(
                f"line {node.lineno}: imports are not allowed; pd, np, px, go are already available"
            )
        if isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                raise CodeValidationError(f"line {node.lineno}: use of '{node.id}' is not allowed")
            if node.id.startswith("__"):
                raise CodeValidationError(f"line {node.lineno}: dunder names are not allowed")
            if node.id == "result" and isinstance(node.ctx, ast.Store):
                assigns_result = True
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES or node.attr.startswith(FORBIDDEN_ATTRIBUTE_PREFIXES):
                raise CodeValidationError(f"line {node.lineno}: attribute '{node.attr}' is not allowed")
        elif isinstance(node, (ast.ClassDef, ast.Global, ast.Nonlocal, ast.AsyncFunctionDef)):
            raise CodeValidationError(f"line {node.lineno}: {type(node).__name__} is not allowed")

    if not assigns_result:
        raise CodeValidationError("code must assign the final answer to a variable named `result`")
