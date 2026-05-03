from click import prompt

from agents.base import BaseAgent
from utils.llm_client import LLMClient

CRITIC_SYSTEM_PROMPT = """你是一个严格的评审专家。请评估以下子任务的执行结果是否符合要求。
原任务：{task}
结果：{result}
评审标准：正确性、完整性、效率。
输出格式：
Decision: PASS 或 FAIL
Feedback: 若 FAIL，给出具体修改建议，否则输出 "无"
"""

class CriticAgent(BaseAgent):
    def __init__(self, model_name: str, llm_client: LLMClient, memory_manager=None):
        super().__init__(model_name, llm_client, memory_manager)
        
    def evaluate(self, task: str, result: str) -> tuple[bool, str]:
        prompt = CRITIC_SYSTEM_PROMPT.format(task=task,result=result)
        response = self.llm.generate(prompt)
        decision = "PASS" if "PASS" in response.upper() else "FAIL"
        if "Feedback: " in response:
            feedback = response.split("Feedback:")[-1].strip()
        else:
            feedback = response
        return decision == "PASS", feedback