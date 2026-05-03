from agents.base import BaseAgent
from utils.llm_client import LLMClient

EXECUTOR_SYSTEM_PROMPT = """你是一个执行专家，负责完成一个具体的子任务。你可以使用提供的工具。
{memory_section}
工具列表：
{tool_descriptions}
回答格式：
若需工具：Thought, Action, Action Input
若完成：Final Answer
"""

class ExecutorAgent(BaseAgent):
    def __init__(self, model_name: str, llm_client: LLMClient, tools_registry=None, memory_manager=None):
        super().__init__(model_name, llm_client, tools_registry, memory_manager)

    def _build_system_prompt(self, task: str) -> str:
        tool_descriptions = "\n".join(
            f"-{tool.name}: {tool.description}" for tool in self.tools
        )
        relevant_memories = self.memory.retrieve_relevant(task, top_k=3)
        memory_section = ""
        if relevant_memories:
            memory_section = "## 相关历史记忆（可能对你有帮助）\n"
            for mem in relevant_memories:
                memory_section += f"- {mem}\n"
        return EXECUTOR_SYSTEM_PROMPT.format(
            memory_section=memory_section,
            tool_descriptions=tool_descriptions,
        ) + f"\n用户任务：{task}"

    def execute_subtask(self, subtask: dict, previous_results: dict[str,str]) -> str:
        """
        执行一个子任务。
        subtask: 包含 id, description 等的字典
        previous_results: 已完成子任务的 id->result 映射
        """
        # 构造上下文：包含前置结果
        context_parts = [f"当前子任务: {subtask['description']}"]
        if subtask.get("depends_on"):
            deps_results = {dep: previous_results.get(dep, "未找到结果") for dep in subtask["depends_on"]}
            deps_text = "\n".join([f"前置任务 {dep_id} 的结果：{res}" for dep_id, res in deps_results.items()])
            context_parts.append(f"前置任务结果：\n{deps_text}")
        
        full_task = "\n".join(context_parts)
        return self.run(full_task)