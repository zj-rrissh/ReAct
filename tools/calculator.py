from pydoc import describe
from tools.base import Tool
from tools.registry import register_tool


@register_tool(name = "calculator")
class CalculatorTool(Tool):
    name = "calculator"
    description = "执行数学计算，输入数学表达式（如 '2+3*4'），返回计算结果"
    
    def execute(self, input: str) -> str:
        try:
            result = eval(input,{"__builtins__": {}},{})
            return str(result)
        except Exception as e:
            return f"计算错误：{str(e)}"
