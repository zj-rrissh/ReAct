import re
import requests
from tools.base import Tool
from tools.registry import register_tool



@register_tool(name="wikipedia")
class WikipediaTool(Tool):
    name = "wikipedia"
    description = ("查询维基百科获取词条摘要和相关信息。"
        "输入搜索关键词（中文或英文），返回相关条目列表和第一条目的详细摘要。")
    
    def execute(self,input: str) -> str:
        return self._search_wiki(input)
    
    def _search_wiki(self,query: str) -> str:
        headers = {"User-Agent": "ReActAgent/1.0 (learn_agent)"}
        try:
            # 先搜索匹配的页面
            search_url = "https://zh.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": 3,
                "srprop": "snippet"
            }
            resp = requests.get(search_url, params=params, headers=headers, timeout=10)
            data = resp.json()
            results = data.get("query", {}).get("search", [])

            if not results:
                return f"未找到与 '{query}' 相关的维基百科条目"

            output = []
            for r in results:
                title = r["title"]
                snippet = re.sub(r'<[^>]+>', '', r.get("snippet", ""))
                output.append(f"• {title}: {snippet}")

            # 取第一个结果获取详细摘要
            first_title = results[0]["title"]
            extract_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "exsentences": 3,
                "titles": first_title
            }
            ext_resp = requests.get(
                "https://zh.wikipedia.org/w/api.php",
                params=extract_params,
                headers=headers,
                timeout=10
            )
            ext_data = ext_resp.json()
            pages = ext_data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if "extract" in page_info and page_id != "-1":
                    output.append(f"\n📖 {first_title} 摘要:\n{page_info['extract']}")
                    break

            return "\n".join(output)

        except Exception as e:
            return f"维基搜索出错: {str(e)}"