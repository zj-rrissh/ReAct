"""CalculatorTool 测试 (16 用例)。"""

import pytest
from tools.calculator import CalculatorTool


@pytest.fixture
def calc():
    return CalculatorTool()


class TestCalculatorTool:
    def test_basic_addition(self, calc):
        assert calc.execute("2+3") == "5"

    def test_basic_subtraction(self, calc):
        assert calc.execute("10-4") == "6"

    def test_multiplication(self, calc):
        assert calc.execute("3*7") == "21"

    def test_division(self, calc):
        assert calc.execute("10/2") == "5.0"

    def test_complex_expression(self, calc):
        assert calc.execute("2+3*4") == "14"

    def test_parentheses_precedence(self, calc):
        assert calc.execute("(2+3)*4") == "20"

    def test_division_by_zero_error_message(self, calc):
        result = calc.execute("1/0")
        assert "错误" in result

    def test_syntax_error_expression(self, calc):
        result = calc.execute("2+*3")
        assert "错误" in result

    def test_empty_string_input(self, calc):
        result = calc.execute("")
        assert "错误" in result

    def test_builtins_blocked_import(self, calc):
        result = calc.execute("__import__('os')")
        assert "错误" in result

    def test_builtins_blocked_open(self, calc):
        result = calc.execute("open('/etc/passwd')")
        assert "错误" in result

    def test_builtins_blocked_exec(self, calc):
        result = calc.execute("exec('print(1)')")
        assert "错误" in result

    def test_builtins_blocked_eval(self, calc):
        result = calc.execute("eval('1+1')")
        assert "错误" in result

    def test_expression_with_spaces(self, calc):
        assert calc.execute(" 2 + 3 ") == "5"

    def test_negative_numbers(self, calc):
        assert calc.execute("-5 + 3") == "-2"

    def test_floating_point_result(self, calc):
        result = calc.execute("7/3")
        assert float(result) == pytest.approx(2.333333, rel=0.01)
