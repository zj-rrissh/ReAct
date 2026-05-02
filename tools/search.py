from tools.base import Tool
from tools.registry import register_tool

@register_tool(name="search")
class SearchTool(Tool):
    name = "search"
    description = "搜索互联网获取信息，输入搜索关键词，返回相关结果摘要"

    def execute(self, input: str) -> str:
        # 这里模拟一个搜索实现，后续可替换为真实 API
        return f"关于 '{input}' 的搜索结果: [示例结果1] [示例结果2]"