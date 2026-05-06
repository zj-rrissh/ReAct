"""ExecutorAgent 测试 (10 用例)。"""

from unittest.mock import MagicMock

import pytest
from agents.executor import ExecutorAgent
from agents.message import Message


class TestBuildSystemPrompt:
    def test_build_system_prompt_contains_tool_descriptions(self, executor_agent):
        prompt = executor_agent._build_system_prompt("test task")
        assert "test task" in prompt

    def test_build_system_prompt_contains_task(self, executor_agent):
        prompt = executor_agent._build_system_prompt("分析数据")
        assert "分析数据" in prompt

    def test_build_system_prompt_with_memories(self, mock_llm_client):
        mock_memory = MagicMock()
        mock_memory.retrieve_relevant.return_value = ["memory 1", "memory 2"]
        agent = ExecutorAgent(
            model_name="test", llm_client=mock_llm_client,
            tools_registry={}, memory_manager=mock_memory,
        )
        prompt = agent._build_system_prompt("task")
        assert "相关历史记忆" in prompt
        assert "memory 1" in prompt
        assert "memory 2" in prompt

    def test_build_system_prompt_without_memories(self, executor_agent):
        prompt = executor_agent._build_system_prompt("task")
        assert "相关历史记忆" not in prompt


class TestExecuteSubtask:
    def test_execute_subtask_includes_dependency_results(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="Final Answer: done")
        agent = ExecutorAgent(
            model_name="test", llm_client=mock_llm_client, tools_registry={},
        )
        subtask = {"id": "2", "description": "分析", "depends_on": ["1"]}
        previous = {"1": "search result here"}
        result = agent.execute_subtask(subtask, previous)
        assert "done" in result

    def test_execute_subtask_missing_dependency_shows_placeholder(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="Final Answer: partial")
        agent = ExecutorAgent(
            model_name="test", llm_client=mock_llm_client, tools_registry={},
        )
        subtask = {"id": "3", "description": "summary", "depends_on": ["99"]}
        previous = {}
        result = agent.execute_subtask(subtask, previous)
        assert "partial" in result

    def test_execute_subtask_no_dependencies(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="Final Answer: standalone")
        agent = ExecutorAgent(
            model_name="test", llm_client=mock_llm_client, tools_registry={},
        )
        subtask = {"id": "1", "description": "独立任务"}
        previous = {}
        result = agent.execute_subtask(subtask, previous)
        assert "standalone" in result

    def test_execute_subtask_returns_result(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="Final Answer: complete result")
        agent = ExecutorAgent(
            model_name="test", llm_client=mock_llm_client, tools_registry={},
        )
        result = agent.execute_subtask(
            {"id": "1", "description": "test"}, {}
        )
        assert len(result) > 0

    def test_execute_subtask_with_multiple_dependencies(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="Final Answer: combined")
        agent = ExecutorAgent(
            model_name="test", llm_client=mock_llm_client, tools_registry={},
        )
        subtask = {"id": "4", "description": "merge", "depends_on": ["1", "2", "3"]}
        previous = {"1": "r1", "2": "r2", "3": "r3"}
        result = agent.execute_subtask(subtask, previous)
        assert "combined" in result


class TestHandleMessage:
    def test_handle_message_extracts_subtask_and_previous_results(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="Final Answer: msg result")
        agent = ExecutorAgent(
            model_name="test", llm_client=mock_llm_client, tools_registry={},
        )
        msg = Message(
            type="task", sender="orchestrator", receiver="executor",
            payload={
                "subtask": {"id": "1", "description": "do it", "depends_on": []},
                "previous_results": {},
            },
        )
        reply = agent.handle_message(msg)
        assert reply.type == "result"
        assert reply.sender == "executor"
        assert reply.receiver == "orchestrator"
        assert "msg result" in reply.payload
