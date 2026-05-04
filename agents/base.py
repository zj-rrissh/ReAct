from abc import ABC
from tools.registry import get_all_tools
from tools.base import Tool
from agents.message import Message
from agents.reviewer import ReviewerAgent
from utils.llm_client import LLMClient
from memory.manager import MemoryManager

class BaseAgent(ABC):
    def __init__(self, model_name: str, llm_client: LLMClient, tools_registry=None, memory_manager=None, name: str = "base_agent"):
        self.model = model_name
        self.name = name
        # 如果传入工具注册表则用它，否则用全局注册表
        tool_classes = (tools_registry or get_all_tools()).values()
        self.tools: list[Tool] = [cls() for cls in tool_classes]# 实例化所有工具
        self.llm = llm_client
        self.memory = memory_manager or MemoryManager()
        
    def _build_system_prompt(self, task: str) -> str:
        """构造包含工具描述的系统提示"""
        tool_descriptions = "\n".join(
            f"-{tool.name}: {tool.description}" for tool in self.tools
        )
        
        relevant_memories = self.memory.retrieve_relevant(task,top_k=3)
        memory_section = ""
        if relevant_memories:
            memory_section = "## 相关历史记忆（可能对你有帮助）\n"
            for mem in relevant_memories:
                memory_section += f"- {mem}\n"
        return f"""你是一个严格遵循 ReAct 模式的智能助理。可用工具：

{tool_descriptions}

{memory_section}

规则：
1. 每次只输出一个 Action。
2. 仔细阅读 Observation，根据结果决定下一步，切勿重复已成功的操作。
3. 只有完成用户所有子任务后才能输出 Final Answer。

格式：
Thought: 你的思考
Action: 工具名称
Action Input: 参数

或（仅当所有子任务完成时）：
Thought: 我知道答案了
Final Answer: 最终答案

用户任务：{task}
"""

    def _parse_all_actions(self, text: str):
        """从模型输出中提取所有 Action-Input 对（支持一次输出多个 Action）"""
        import re
        actions = re.findall(r"Action:\s*(\S+)", text)
        inputs = re.findall(r"Action Input:\s*(.+?)(?=\nAction:|\nFinal Answer:|\Z)", text, re.DOTALL)
        return list(zip(actions, inputs))
    
    def run(self, task: str, max_steps: int = 20) -> str:
        """执行 ReAct 循环"""
        prompt = self._build_system_prompt(task)
        context = prompt
        self.current_task = task
        if not hasattr(self, 'original_task'):
            self.original_task = task
        
        for step in range(max_steps):
            #  1. 调用 LLM
            response = self._call_llm(context)
            print(f"\n{'='*60}")
            print(f"[Agent] 第 {step+1} 步 模型原始输出:\n{response}")

            # 2. 解析所有 Action（一次响应可能包含多个）
            action_pairs = self._parse_all_actions(response)
            if action_pairs:
                for action_name, action_input in action_pairs:
                    # 3. 执行工具
                    print(f"[Agent] 调用工具: {action_name}, 输入: {action_input}")
                    tool = next((t for t in self.tools if t.name == action_name), None)
                    if tool is None:
                        observation = f"工具 '{action_name}' 不存在，可用工具: {[t.name for t in self.tools]}"
                    else:
                        try:
                            observation = tool.execute(action_input) # type: ignore
                        except Exception as e:
                            observation = f"工具执行出错: {str(e)}"
                        self.memory.add_from_tool_result(
                            task=self.original_task,  # 需保存原始任务描述，可在 __init__ 中记录
                            tool_name=action_name,
                            input=action_input,
                            output=observation
                        )
                    print(f"[Agent] 工具返回: {observation}")
                    # 4. 将观察结果加入上下文
                    context += f"\nObservation: {observation}\n"
                continue

            # 5. 没有 Action 时，检查 Final Answer
            if "Final Answer:" in response:
                final = response.split("Final Answer:")[-1].strip()
                return final

            # 如果解析失败，视为最终答案尝试
            return response
            
        return "达到最大步数，任务未完成。"
            
            
    def _call_llm(self, prompt: str) -> str:
        return self.llm.generate(prompt)

    def run_with_reflection(self, task: str, max_retries: int = 2, max_steps: int = 20) -> str: # type: ignore
        reviewer = ReviewerAgent(model_name=self.model,llm_client=self.llm)
        current_task = task
        for attempt in range(max_retries +1):
            # 执行任务
            answer = self.run(current_task, max_steps=max_steps)

            # 评审（通过 Message 与 Reviewer 通信）
            review_msg = Message(
                type="task",
                sender=self.name,
                receiver=reviewer.name,
                payload={"task": current_task, "answer": answer},
            )
            review_response = reviewer.handle_message(review_msg)
            passed = review_response.payload["passed"]
            feedback = review_response.payload["feedback"]

            print(f"\n{'─'*60}")
            print(f"[Reviewer] 第 {attempt+1} 次评审结果: {'✅ PASS' if passed else '❌ FAIL'}")
            print(f"[Reviewer] 评审意见:\n{feedback}")
            print(f"{'─'*60}")

            if passed:
                return answer
            self.memory.add_reflection_insight(task=task, feedback=feedback)
            if attempt < max_retries:
                print(f"[Reflection] 准备根据反馈进行第 {attempt+2} 次尝试...\n")
                current_task = (
                    f"上一次尝试回答以下任务失败，评审反馈：{feedback}\n\n"
                    f"请根据反馈重新回答，确保更准确、完整。\n"
                    f"原始任务：{task}"
                )
            else:
                return f"经过{max_retries}次修正仍未通过评审，最终答案如下（反馈：{feedback}）：\n{answer}"
            
            