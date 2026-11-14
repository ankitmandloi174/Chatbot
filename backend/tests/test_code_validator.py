import pytest

from app.services.analysis.code_validator import CodeValidationError, validate_code


def test_accepts_valid_code():
    validate_code("result = sales.groupby('region')['revenue'].sum()")


@pytest.mark.parametrize(
    "code",
    [
        "import os\nresult = 1",
        "from os import path\nresult = 1",
        "result = open('/etc/passwd').read()",
        "result = eval('1+1')",
        "result = pd.read_csv('x.csv')",
        "sales.to_csv('x.csv')\nresult = 1",
        "result = sales.__class__",
        "result = pd.io.common.os.system('ls')",
        "result = getattr(sales, 'shape')",
        "class A: pass\nresult = 1",
        "x = 1",  # never assigns result
        "result = (",  # syntax error
    ],
)
def test_rejects_unsafe_or_invalid_code(code: str):
    with pytest.raises(CodeValidationError):
        validate_code(code)
