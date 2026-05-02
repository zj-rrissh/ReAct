import re
from dotenv import load_dotenv
import ollama
import requests




SYSTEM_PROMPT = """你是一个可以使用工具的AI助手。请严格按以下格式与系统交互:

每次你只能输出一步：
- 如果需要工具：输出 Thought 和 Action
- 如果已有足够信息：直接输出 Final Answer

格式示例（一轮对话）:

--- 示例1: 需要调用工具 ---
用户: 计算 15+23*2 的结果
助手: Thought: 这是一个数学计算，需要调用计算器工具。
Action: calculator [15+23*2]
系统: Observation: 61
助手: Thought: 计算完成。
Final Answer: 15+23*2 的结果是 61。

--- 示例2: 无需工具 ---
用户: 你好
助手: Final Answer: 你好！有什么可以帮你的吗？

重要规则:
1. 每次只输出一步，不要提前模拟 Observation 或 Final Answer
2. 工具结果会通过 Observation 返回给你，你只需要等待
3. 如果不需要工具，直接给出 Final Answer

可用工具：
- calculator: 数学计算器，输入数学表达式，例如 Action: calculator [15+23*2]
- search: 维基百科搜索，输入搜索关键词，例如 Action: search [Python编程语言]


"""


def agent_loop(prompt, tools, model = "qwen2.5:1.5b",max_steps=10):
    messages = [{'role': 'system','content': SYSTEM_PROMPT},
                {'role': 'user','content': prompt}]
    
    for step in range(max_steps):
        #1.Thoughts 模型思考
        response = ollama.chat(model=model,
                               messages=messages)
        text = response['message']['content']
        
        print(f"\n{'='*40}\nStep {step+1} 模型原始输出:\n{text}\n{'='*40}")

        #2.Action 优先解析 — 只要输出中有 Action 就强制执行工具
        # 兼容 Action: tool [param] 和 Action: tool param 两种格式
        action_match = re.search(r'Action:\s*(\w+)\s*\[(.*?)\]', text, re.DOTALL)
        if not action_match:
            action_match = re.search(r'Action:\s*(\w+)\s+(.+?)(?:\n|$)', text)
        if action_match:
            tool_name = action_match.group(1)
            tool_input = action_match.group(2).strip()
            print(f"🔧 调用工具: {tool_name}({tool_input})")

            # 工具调用
            if tool_name in tools:
                try:
                    result = tools[tool_name](tool_input)
                    print(f"📊 工具返回: {result}")
                except Exception as e:
                    result = f"工具执行错误: {str(e)}"
            else:
                result = f"错误: 工具 '{tool_name}' 不存在。可用工具: {list(tools.keys())}"

            messages.append({'role': 'assistant', 'content': text})
            messages.append({'role': 'user',
                            'content': f'Observation: {result}'})
            continue

        # 无 Action，检查是否有 Final Answer
        final_match = re.search(r'Final Answer:\s*(.*)',text,re.DOTALL)
        if final_match:
            print("✅ 检测到 Final Answer")
            return final_match.group(1).strip()

        # 既无 Action 也无 Final Answer，要求重新思考
        print("⚠️ 未检测到 Action/Final Answer，要求模型重新思考...")
        messages.append({'role': 'assistant','content': text})
        messages.append({'role': 'user','content': '请严格按格式输出。需要工具则使用 "Action: 工具名[参数]"，否则用 "Final Answer: 答案"。'})
        continue
    #3.Observation 观察输出,判断是否超过最大循环次数，是否需要循环
    #final answer
    messages.append({'role': 'user',
                    'content': '已达到最大步数限制，请立即给出 Final Answer。'})
    final_response = ollama.chat(model=model, messages=messages)
    final_text = final_response['message']['content']

    final_match = re.search(r'Final Answer:\s*(.*)', final_text, re.DOTALL)
    if final_match:
        return final_match.group(1).strip()
    return final_text


def calculator(expr):
    """数学计算器 - 使用 eval 计算数学表达式"""
    # 只允许数字、运算符、括号、空格、小数点
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expr):
        return "错误: 表达式包含非法字符"
    try:
        return str(eval(expr))
    except Exception as e:
        return f"计算错误: {str(e)}"


def search_wiki(query):
    """维基百科搜索 - 查询 Wikipedia 并返回摘要"""
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
        extract_url = "https://zh.wikipedia.org/w/api.php"
        extract_params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "exsentences": 3,
            "titles": first_title
        }
        ext_resp = requests.get(extract_url, params=extract_params, headers=headers, timeout=10)
        ext_data = ext_resp.json()
        pages = ext_data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            if "extract" in page_info and page_id != "-1":
                output.append(f"\n📖 {first_title} 摘要:\n{page_info['extract']}")
                break

        return "\n".join(output)
    except Exception as e:
        return f"维基搜索出错: {str(e)}"


tools = {"calculator": calculator, "search": search_wiki}

user_input = input("user: ")
result = agent_loop(user_input, tools)
print(result)
