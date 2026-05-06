from tools.registry import register_tool
from tools.base import Tool
from duckduckgo_search import DDGS

@register_tool(name="web_search")
class WebSearchTool(Tool):
    name = "web_search"
    description = ("使用搜索引擎搜索互联网,输入搜索关键词,返回结果标题、链接和摘要。"
        "适用于查找维基百科之外的实时或广泛信息。"
        "例如：使用网络搜索最近新闻")

    def execute(self, input: str) -> str:
        return self._search_web(input)
    
    def _search_web(self, query: str) -> str:
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append(f"标题: {r['title']}\n链接: {r['href']}\n摘要: {r['body']}\n")
            if not results:
                return "未找到相关结果"
            return "\n".join(results)
        except Exception as e:
            return f"搜索失败: {str(e)}"
            