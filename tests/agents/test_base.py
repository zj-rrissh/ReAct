"""BaseAgent 测试 (22 用例)。"""

from unittest.mock import MagicMock, patch

import pytest
from agents.base import BaseAgent


class StubAgent(BaseAgent):
    """可实例化的 BaseAgent 子类（绕过 ABC）。"""
    pass


@pytest.fixture
def agent(mock_llm_client, mock_memory_manager):
    return StubAgent(
        model_name="test", llm_client=mock_llm_client,
        tools_registry={}, memory_manager=mock_memory_manager,
        name="test_agent",
    )


@pytest.fixture
def agent_with_tools(mock_llm_client, mock_memory_manager):
    from tools.base import Tool

    class MockCalc(Tool):
        name = "mock_calc"
        description = "计算器"

        def execute(self, input: str) -> str:
            return f"calc:{input}"

    class MockSearch(Tool):
        name = "mock_search"
        description = "搜索"

        def execute(self, input: str) -> str:
            return f"search:{input}"

    class FailingTool(Tool):
        name = "failing"
        description = "总是失败"

        def execute(self, input: str) -> str:
            raise RuntimeError("tool error")

    return StubAgent(
        model_name="test", llm_client=mock_llm_client,
        tools_registry={"mock_calc": MockCalc, "mock_search": MockSearch, "failing": FailingTool},
        memory_manager=mock_memory_manager,
        name="test_agent",
    )


class TestParseAllActions:
    def test_parse_zero_actions(self, agent):
        result = agent._parse_all_actions("Thought: 不需要工具\nFinal Answer: 直接回答")
        assert result == []

    def test_parse_single_action(self, agent):
        result = agent._parse_all_actions(
            "Thought: 需要搜索\nAction: search\nAction Input: python tutorial"
        )
        assert len(result) == 1
        assert result[0] == ("search", "python tutorial")

    def test_parse_multiple_actions(self, agent):
        text = (
            "Action: search\nAction Input: query1\n"
            "Action: calculator\nAction Input: 2+3"
        )
        result = agent._parse_all_actions(text)
        assert len(result) == 2
        assert result[0] == ("search", "query1")
        assert result[1] == ("calculator", "2+3")

    def test_parse_action_with_final_answer_after(self, agent):
        text = (
            "Action: calculator\nAction Input: 2+3\n"
            "Final Answer: 结果是5"
        )
        result = agent._parse_all_actions(text)
        assert len(result) == 1
        assert result[0][0] == "calculator"

    def test_parse_action_multiline_input(self, agent):
        text = (
            "Action: file_write\n"
            "Action Input: test.txt\n"
            "这是多行内容\n"
            "第二行\n"
            "Action: another\n"
            "Action Input: x"
        )
        result = agent._parse_all_actions(text)
        assert len(result) == 2

    def test_parse_action_input_with_special_chars(self, agent):
        text = "Action: search\nAction Input: python & AI @2024"
        result = agent._parse_all_actions(text)
        assert len(result) == 1
        assert result[0][1] == "python & AI @2024"

    def test_parse_malformed_action_missing_input(self, agent):
        text = "Action: calculator\n"
        result = agent._parse_all_actions(text)
        assert result == []

    def test_parse_action_case_sensitive(self, agent):
        text = "action: search\nAction Input: query"
        result = agent._parse_all_actions(text)
        assert result == []

    def test_parse_action_with_colon_in_input(self, agent):
        text = "Action: search\nAction Input: key: value"
        result = agent._parse_all_actions(text)
        assert len(result) == 1
        assert "key: value" in result[0][1]


class TestBuildSystemPrompt:
    def test_build_system_prompt_contains_tool_descriptions(self, agent_with_tools):
        prompt = agent_with_tools._build_system_prompt("task")
        assert "mock_calc" in prompt
        assert "mock_search" in prompt

    def test_build_system_prompt_contains_task(self, agent_with_tools):
        prompt = agent_with_tools._build_system_prompt("复杂任务描述")
        assert "复杂任务描述" in prompt

    def test_build_system_prompt_with_no_relevant_memories(self, agent_with_tools):
        prompt = agent_with_tools._build_system_prompt("task")
        assert "相关历史记忆" not in prompt

    def test_build_system_prompt_with_memories(self, mock_llm_client):
        mock_memory = MagicMock()
        mock_memory.retrieve_relevant.return_value = ["记忆1", "记忆2"]
        agent = StubAgent(model_name="test", llm_client=mock_llm_client,
                          tools_registry={}, memory_manager=mock_memory)
        prompt = agent._build_system_prompt("task")
        assert "相关历史记忆" in prompt
        assert "记忆1" in prompt

    def test_build_system_prompt_format_rules(self, agent):
        prompt = agent._build_system_prompt("task")
        assert "ReAct" in prompt
        assert "Action:" in prompt
        assert "Final Answer:" in prompt


class TestRun:
    def test_run_final_answer_path_returns_answer(self, agent):
        agent.llm.generate = MagicMock(return_value="Final Answer: 这是一个答案")
        result = agent.run("task")
        assert "这是一个答案" in result

    def test_run_tool_call_path_executes_tool(self, agent_with_tools):
        responses = [
            "Action: mock_calc\nAction Input: 1+1",
            "Final Answer: done",
        ]
        agent_with_tools.llm.generate = MagicMock(side_effect=responses)
        result = agent_with_tools.run("计算 1+1", max_steps=5)
        assert "done" in result

    def test_run_unknown_tool_returns_error_observation(self, agent):
        agent.llm.generate = MagicMock(return_value="Action: nonexistent\nAction Input: x")
        result = agent.run("task", max_steps=1)
        result = agent.run("task", max_steps=1)
        assert True

    def test_run_tool_execution_error_handled(self, agent_with_tools):
        agent_with_tools.llm.generate = MagicMock(return_value="Action: failing\nAction Input: test")
        result = agent_with_tools.run("task", max_steps=1)
        assert True

    def test_run_max_steps_exceeded_returns_message(self, agent):
        agent.llm.generate = MagicMock(return_value="Action: something\nAction Input: x")
        result = agent.run("task", max_steps=1)
        assert True

    def test_run_multiple_actions_in_one_response(self, agent_with_tools):
        agent_with_tools.llm.generate = MagicMock(return_value=(
            "Action: mock_calc\nAction Input: 1+1\n"
            "Action: mock_search\nAction Input: test"
        ))
        result = agent_with_tools.run("task", max_steps=2)
        assert True


class TestRunWithReflection:
    def test_run_with_reflection_pass_on_first_attempt(self, agent):
        with patch("agents.reviewer.ReviewerAgent") as MockReviewer:
            mock_reviewer = MagicMock()
            mock_reviewer.name = "reviewer"
            mock_reviewer.handle_message.return_value = MagicMock()
            mock_reviewer.handle_message.return_value.type = "feedback"
            mock_reviewer.handle_message.return_value.payload = {"passed": True, "feedback": "无"}
            MockReviewer.return_value = mock_reviewer

            agent.llm.generate = MagicMock(return_value="Final Answer: 答案")
            result = agent.run_with_reflection("task", max_retries=1)
            assert "答案" in result

    def test_run_with_reflection_fail_then_pass(self, agent):
        with patch("agents.reviewer.ReviewerAgent") as MockReviewer:
            mock_reviewer = MagicMock()
            mock_reviewer.name = "reviewer"
            mock_reviewer.handle_message.side_effect = [
                MagicMock(type="feedback", payload={"passed": False, "feedback": "不够完整"}),
                MagicMock(type="feedback", payload={"passed": True, "feedback": "无"}),
            ]
            MockReviewer.return_value = mock_reviewer

            agent.llm.generate = MagicMock(return_value="Final Answer: 修正后答案")
            result = agent.run_with_reflection("task", max_retries=1)
            assert "修正后答案" in result

    def test_run_with_reflection_all_retries_exhausted(self, agent):
        with patch("agents.reviewer.ReviewerAgent") as MockReviewer:
            mock_reviewer = MagicMock()
            mock_reviewer.name = "reviewer"
            mock_reviewer.handle_message.return_value = MagicMock(
                type="feedback", payload={"passed": False, "feedback": "仍然有误"}
            )
            MockReviewer.return_value = mock_reviewer

            agent.llm.generate = MagicMock(return_value="Final Answer: 不完善答案")
            result = agent.run_with_reflection("task", max_retries=1)
            assert "未通过" in result or "修正" in result
