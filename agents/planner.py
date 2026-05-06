from typing import List

from agents.base import BaseAgent
from agents.message import Message
from agents.plan_graph import PlanGraph, TaskNode
from utils.llm_client import LLMClient

PLANNER_SYSTEM_PROMPT = """你是一个任务规划专家。你的任务是将用户提出的复杂请求分解为一系列可独立执行的子任务。
每个子任务应该清晰、具体，且可以被单一工具或简单工具链解决。

当前可用工具及说明：
{tool_descriptions}

输出格式必须严格按照 JSON 数组：
[
  {{"id": "1", "description": "子任务描述", "depends_on": [], "assigned_to": "executor"}},
  {{"id": "2", "description": "子任务描述", "depends_on": ["1"], "assigned_to": "executor"}}
]
注意：
- 每个子任务应有唯一 id。
- depends_on 列出必须在此之前完成的子任务 id 列表。
- assigned_to 固定为 "executor"（后续可扩展）。
- 子任务描述应明确指出应使用哪个工具、以及具体参数（如文件路径、内容等）。
- 仅输出 JSON 数组，不要包含其他文字。
"""


REPLAN_PROMPT = """你是一个任务规划专家。之前的计划部分子任务执行失败，请根据当前进度和失败反馈，调整剩余子任务的计划。
原始任务：{original_task}
已完成子任务及其结果：{completed}
失败子任务及反馈：{failed}
剩余未执行子任务：{pending}
请输出调整后的剩余子任务计划（JSON数组，格式与初始计划相同，但只包含尚未成功完成的部分）。
注意：可以更改描述、合并子任务、修改依赖，但必须确保最终能完成原始任务。"""

class PlannerAgent(BaseAgent):
    def __init__(self, model_name: str, llm_client: LLMClient, memory_manager=None, name: str = "planner"):
        super().__init__(model_name, llm_client, tools_registry={}, memory_manager=memory_manager, name=name)

        tool_descriptions = "\n".join(
            f"- {tool.name}: {tool.description}" for tool in self.tools
        )
        self.system_prompt = PLANNER_SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)
        
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
            for item in plan:
                if "id" not in item or "description" not in item:
                    print("[Planner] 计划格式无效（缺少id/description），使用单步回退")
                    return [{"id": "1", "description": task, "depends_on": [], "assigned_to": "executor"}]
            return plan
        except Exception:
            return [{"id": "1", "description": task, "depends_on": [], "assigned_to": "executor"}]

    def handle_message(self, msg: Message) -> Message:
        plan = self.plan(msg.payload)
        return msg.create_reply(plan, "result")
    
    def replan(self,original_task: str, graph: PlanGraph, failed_nodes: List[TaskNode]) -> List[dict]:
        completed = {node.id: node.result for node in graph.nodes.values() if node.status == "done"}
        pending = [node.id for node in graph.nodes.values() if node.status == "pending"]
        failed_info = [f"ID:{n.id}, 描述:{n.description}, 失败次数:{n.attempts}" for n in failed_nodes]
        
        prompt = REPLAN_PROMPT.format(original_task = original_task,
                                      completed = completed,
                                      failed = failed_info,
                                      pending = pending)
        response = self.llm.generate(prompt=prompt)
        import json
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1].rsplit("\n", 1)[0]
            new_plan = json.loads(json_str)
            return new_plan
        except Exception:
            print("[Planner] replan JSON 解析失败，回退到原计划")
            return []   # 降级：保持原计划不变