from agents.message import Message
from utils.llm_client import LLMClient


REVIEWER_SYSTEM_PROMPT = """你是一个严格的评审专家。你的任务是检查以下问题的答案是否正确、完整和高效。

请按以下格式输出评审结果：

- 如果答案完全满足要求，输出：PASS
- 如果答案有缺陷，输出：FAIL 并给出具体修改建议

输出格式：
Decision: PASS 或 FAIL
Feedback: <如果 FAIL，请给出清晰、可操作的修改建议；如果 PASS，写 "无">

以下是需要评审的任务和答案：

任务：{task}
答案：{answer}

请评审："""

class ReviewerAgent:
    def __init__(self, model_name: str, llm_client: LLMClient, name: str = "reviewer"):
        self.model = model_name
        self.llm = llm_client
        self.name = name
        
    def review(self,task: str,answer: str) -> tuple[bool, str]:
        """返回（是否通过，反馈信息）"""
        prompt = REVIEWER_SYSTEM_PROMPT.format(task=task, answer=answer)
        response = self._call_llm(prompt)

        # 解析 Decision 和 Feedback
        decision, feedback = self._parse_review(response)
        return decision, feedback

    
    def _call_llm(self, prompt: str) -> str:
        return self.llm.generate(prompt)
    
    def _parse_review(self, response: str) -> tuple[bool, str]:
        # 从 Decision: 行提取判断结果，避免 Feedback 文本中出现的 PASS/FAIL 干扰
        passed = False
        if "Decision:" in response:
            decision_part = response.split("Decision:")[-1].split("\n")[0].strip().upper()
            passed = decision_part.startswith("PASS")

        if "Feedback:" in response:
            feedback = response.split("Feedback:")[-1].strip()
        else:
            feedback = response.strip()
        return passed, feedback

    def handle_message(self, msg: Message) -> Message:
        passed, feedback = self.review(msg.payload["task"], msg.payload["answer"])
        return msg.create_reply({"passed": passed, "feedback": feedback}, "feedback")

    