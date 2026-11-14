"""Which datasets and columns did the generated code actually reference?"""

import ast


def referenced_columns(code: str, columns_by_table: dict[str, list[str]]) -> dict[str, list[str]]:
    """Map each dataset the code touches to the columns it names.

    A dataset counts as used when its variable appears in the code (or `dfs["name"]`);
    a column counts when its name appears as a string literal or attribute (`df.col`).
    Columns created by the code itself are not listed because they are not in the source data.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)

    return {
        table: [c for c in columns if c in names]
        for table, columns in columns_by_table.items()
        if table in names
    }
