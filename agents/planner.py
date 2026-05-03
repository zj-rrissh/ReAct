from click import prompt

from agents.base import BaseAgent
from utils.llm_client import LLMClient

PLANNER_SYSTEM_PROMPT = """你是一个任务规划专家。你的任务是将用户提出的复杂请求分解为一系列可独立执行的子任务。
每个子任务应该清晰、具体，且可以被单一工具或简单工具链解决。
输出格式必须严格按照 JSON 数组：
[
  {"id": "1", "description": "子任务描述", "depends_on": [], "assigned_to": "executor"},
  {"id": "2", "description": "子任务描述", "depends_on": ["1"], "assigned_to": "executor"}
]
注意：
- 每个子任务应有唯一 id。
- depends_on 列出必须在此之前完成的子任务 id 列表。
- assigned_to 固定为 "executor"（后续可扩展）。
- 仅输出 JSON 数组，不要包含其他文字。
"""

class PlannerAgent(BaseAgent):
    def __init__(self, model_name: str, llm_client: LLMClient, memory_manager=None):
        super().__init__(model_name, llm_client, tools_registry={}, memory_manager=memory_manager)
        
        self.system_prompt = PLANNER_SYSTEM_PROMPT
        
    def plan(self, task: str) -> list[dict]:
        """生成任务计划，返回任务列表"""
        prompt = f"{self.system_prompt}\n\n用户任务：{task}"
        response = self.llm.generate(prompt=prompt)

        import json
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1].rsplit("\n", 1)[0]
            plan = json.loads(json_str)
            return plan
        except Exception:
            return [{"id": "1", "description": task, "depends_on": [], "assigned_to": "executor"}]