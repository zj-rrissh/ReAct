"""PlannerAgent 测试 (15 用例)。"""

import json
from unittest.mock import MagicMock

import pytest
from agents.planner import PlannerAgent
from agents.message import Message


@pytest.fixture
def valid_plan_json():
    return json.dumps([
        {"id": "1", "description": "搜索数据", "depends_on": [], "assigned_to": "executor"},
        {"id": "2", "description": "分析数据", "depends_on": ["1"], "assigned_to": "executor"},
    ])


class TestPlan:
    def test_plan_returns_valid_json_list(self, mock_llm_client, valid_plan_json):
        mock_llm_client.generate = MagicMock(return_value=valid_plan_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("分析数据")
        assert len(plan) == 2
        assert plan[0]["id"] == "1"

    def test_plan_parses_markdown_code_block_json(self, mock_llm_client, valid_plan_json):
        markdown_json = f"```json\n{valid_plan_json}\n```"
        mock_llm_client.generate = MagicMock(return_value=markdown_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("分析数据")
        assert len(plan) == 2

    def test_plan_parses_json_with_no_code_block(self, mock_llm_client, valid_plan_json):
        mock_llm_client.generate = MagicMock(return_value=f"   {valid_plan_json}   ")
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("分析数据")
        assert len(plan) == 2

    def test_plan_fallback_on_json_parse_error(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="这不是 JSON")
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("任何任务")
        assert len(plan) == 1
        assert plan[0]["id"] == "1"
        assert plan[0]["description"] == "任何任务"

    def test_plan_fallback_on_missing_id_field(self, mock_llm_client):
        bad_json = json.dumps([{"description": "missing id", "depends_on": []}])
        mock_llm_client.generate = MagicMock(return_value=bad_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("task")
        assert len(plan) == 1
        assert plan[0]["id"] == "1"

    def test_plan_fallback_on_missing_description_field(self, mock_llm_client):
        bad_json = json.dumps([{"id": "1", "depends_on": []}])
        mock_llm_client.generate = MagicMock(return_value=bad_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("task")
        assert len(plan) == 1
        assert plan[0]["description"] == "task"

    def test_plan_fallback_on_both_missing_fields(self, mock_llm_client):
        bad_json = json.dumps([{"assigned_to": "executor"}])
        mock_llm_client.generate = MagicMock(return_value=bad_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("task")
        assert len(plan) == 1

    def test_plan_with_dependencies_in_response(self, mock_llm_client):
        deps_json = json.dumps([
            {"id": "a", "description": "A", "depends_on": [], "assigned_to": "executor"},
            {"id": "b", "description": "B", "depends_on": ["a"], "assigned_to": "executor"},
        ])
        mock_llm_client.generate = MagicMock(return_value=deps_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("task")
        assert plan[1]["depends_on"] == ["a"]

    def test_plan_fallback_returns_single_step_structure(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="invalid json")
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        plan = agent.plan("complex task")
        assert len(plan) == 1
        assert plan[0]["depends_on"] == []
        assert plan[0]["assigned_to"] == "executor"


class TestReplan:
    def test_replan_returns_valid_json(self, mock_llm_client, valid_plan_json):
        mock_llm_client.generate = MagicMock(return_value=valid_plan_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        from agents.plan_graph import PlanGraph, TaskNode
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "old", "depends_on": []}])
        g.mark_failed("1", "error")
        failed = g.get_failed_nodes()
        new_plan = agent.replan("task", g, failed)
        assert len(new_plan) == 2

    def test_replan_parses_markdown_code_block(self, mock_llm_client, valid_plan_json):
        mock_llm_client.generate = MagicMock(return_value=f"```\n{valid_plan_json}\n```")
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "old", "depends_on": []}])
        g.mark_failed("1", "error")
        new_plan = agent.replan("task", g, g.get_failed_nodes())
        assert len(new_plan) == 2

    def test_replan_fallback_returns_empty_list(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="not json at all")
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "old", "depends_on": []}])
        g.mark_failed("1", "error")
        new_plan = agent.replan("task", g, g.get_failed_nodes())
        assert new_plan == []

    def test_replan_with_no_failed_nodes(self, mock_llm_client, valid_plan_json):
        mock_llm_client.generate = MagicMock(return_value=valid_plan_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan([{"id": "1", "description": "ok", "depends_on": []}])
        g.mark_done("1", "result")
        new_plan = agent.replan("task", g, [])
        assert len(new_plan) == 2


class TestHandleMessage:
    def test_handle_message_calls_plan_and_returns_reply(self, mock_llm_client, valid_plan_json):
        mock_llm_client.generate = MagicMock(return_value=valid_plan_json)
        agent = PlannerAgent(model_name="test", llm_client=mock_llm_client)
        msg = Message(type="task", sender="orchestrator", receiver="planner", payload="test task")
        reply = agent.handle_message(msg)
        assert reply.type == "result"
        assert reply.sender == "planner"
        assert reply.receiver == "orchestrator"
        assert isinstance(reply.payload, list)
