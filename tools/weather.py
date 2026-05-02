from tools.base import Tool
from tools.registry import register_tool

@register_tool(name="weather")
class WeatherTool(Tool):
    name = "weather"
    description = "查询某个城市的天气，输入城市名称，返回天气信息。例如：今天南京的天气怎么样？"
    
    def execute(self, input: str | None) -> str:
        return f"{input}的天气：晴，25°C"   # 模拟