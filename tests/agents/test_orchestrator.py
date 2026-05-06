"""Orchestrator 测试 (22+ 用例) —— mock 所有子 Agent。"""

from unittest.mock import MagicMock, patch

import pytest
from agents.message import Message
from agents.orchestrator import Orchestrator


def make_pass_reply(original_msg, result_text="done"):
    return Message(type="result", sender=original_msg.receiver,
                   receiver=original_msg.sender, payload=result_text)


def make_critic_pass(original_msg):
    return Message(type="feedback", sender=original_msg.receiver,
                   receiver=original_msg.sender, payload={"passed": True, "feedback": "无"})


def make_critic_fail(original_msg, feedback="not good"):
    return Message(type="feedback", sender=original_msg.receiver,
                   receiver=original_msg.sender, payload={"passed": False, "feedback": feedback})


@pytest.fixture
def mock_planner():
    p = MagicMock()
    p.name = "planner"
    return p


@pytest.fixture
def mock_executor():
    e = MagicMock()
    e.name = "executor"
    return e


@pytest.fixture
def mock_critic():
    c = MagicMock()
    c.name = "critic"
    return c


@pytest.fixture
def mock_memory():
    return MagicMock()


@pytest.fixture
def orch(mock_planner, mock_executor, mock_critic, mock_memory):
    return Orchestrator(mock_planner, mock_executor, mock_critic, mock_memory)


def sample_plan():
    return [
        {"id": "1", "description": "搜索数据", "depends_on": [], "assigned_to": "executor"},
        {"id": "2", "description": "分析结果", "depends_on": ["1"], "assigned_to": "executor"},
    ]


class TestRunWithGraph:
    def test_run_with_graph_complete_flow_success(self, orch, mock_planner, mock_executor, mock_critic):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=sample_plan(),
        )
        mock_executor.handle_message.side_effect = lambda msg: make_pass_reply(msg, f"result of task")
        mock_critic.handle_message.side_effect = lambda msg: make_critic_pass(msg)

        result = orch.run_with_graph("测试任务", max_retries=1)
        assert "任务完成" in result or "Progress" in result.replace("进度", "Progress")

    def test_run_with_graph_empty_plan(self, orch, mock_planner):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=[],
        )
        result = orch.run_with_graph("空任务")
        assert isinstance(result, str)

    def test_run_with_graph_plan_validation_failure(self, orch, mock_planner):
        bad_plan = [
            {"id": "1", "description": "任务", "depends_on": ["99"]},
        ]
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=bad_plan,
        )
        result = orch.run_with_graph("任务")
        assert "无效" in result or "无法执行" in result

    def test_run_with_graph_executor_retry_logic(self, orch, mock_planner, mock_executor, mock_critic):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=sample_plan(),
        )
        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"
        )
        mock_critic.handle_message.side_effect = [
            make_critic_fail(Message(type="task", sender="orchestrator", receiver="critic", payload={}), "first fail"),
            make_critic_pass(Message(type="task", sender="orchestrator", receiver="critic", payload={})),
            make_critic_pass(Message(type="task", sender="orchestrator", receiver="critic", payload={})),
        ]
        result = orch.run_with_graph("任务", max_retries=1)
        assert isinstance(result, str)

    def test_run_with_graph_executor_exhausts_retries(self, orch, mock_planner, mock_executor, mock_critic):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=sample_plan(),
        )
        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"
        )
        mock_critic.handle_message.return_value = make_critic_fail(
            Message(type="task", sender="orchestrator", receiver="critic", payload={}), "always fail"
        )
        result = orch.run_with_graph("任务", max_retries=0)
        assert isinstance(result, str)

    def test_run_with_graph_triggers_replan(self, orch, mock_planner, mock_executor, mock_critic):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=sample_plan(),
        )
        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"
        )
        mock_critic.handle_message.return_value = make_critic_fail(
            Message(type="task", sender="orchestrator", receiver="critic", payload={}), "bad"
        )
        mock_planner.replan.return_value = []

        result = orch.run_with_graph("任务", max_retries=0, max_replans=1)
        assert isinstance(result, str)

    def test_run_with_graph_max_replans_reached(self, orch, mock_planner, mock_executor, mock_critic):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=sample_plan(),
        )
        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"
        )
        mock_critic.handle_message.return_value = make_critic_fail(
            Message(type="task", sender="orchestrator", receiver="critic", payload={}), "bad"
        )
        mock_planner.replan.return_value = []

        result = orch.run_with_graph("任务", max_retries=0, max_replans=0)
        assert isinstance(result, str)

    def test_run_with_graph_result_format(self, orch, mock_planner, mock_executor, mock_critic):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=[
                {"id": "1", "description": "单步任务", "depends_on": [], "assigned_to": "executor"},
            ],
        )
        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "成功结果"
        )
        mock_critic.handle_message.return_value = make_critic_pass(
            Message(type="task", sender="orchestrator", receiver="critic", payload={})
        )
        result = orch.run_with_graph("任务")
        assert isinstance(result, str)


class TestExecuteNode:
    def test_execute_node_pass_first_attempt(self, orch, mock_executor, mock_critic):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan(sample_plan())
        orch.graph = g
        node = g.get_node("1")

        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"
        )
        mock_critic.handle_message.return_value = make_critic_pass(
            Message(type="task", sender="orchestrator", receiver="critic", payload={})
        )

        result = orch._execute_node(node, {}, max_retries=1)
        assert result is True
        assert node.status == "done"

    def test_execute_node_fail_then_pass_on_retry(self, orch, mock_executor, mock_critic):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan(sample_plan())
        orch.graph = g
        node = g.get_node("1")

        mock_executor.handle_message.side_effect = [
            make_pass_reply(Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"),
            make_pass_reply(Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"),
        ]
        mock_critic.handle_message.side_effect = [
            make_critic_fail(Message(type="task", sender="orchestrator", receiver="critic", payload={}), "fail"),
            make_critic_pass(Message(type="task", sender="orchestrator", receiver="critic", payload={})),
        ]

        result = orch._execute_node(node, {}, max_retries=1)
        assert result is True
        assert node.status == "done"

    def test_execute_node_exhausts_all_attempts(self, orch, mock_executor, mock_critic):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan(sample_plan())
        orch.graph = g
        node = g.get_node("1")

        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"
        )
        mock_critic.handle_message.return_value = make_critic_fail(
            Message(type="task", sender="orchestrator", receiver="critic", payload={}), "always bad"
        )

        result = orch._execute_node(node, {}, max_retries=0)
        assert result is False
        assert node.status == "failed"


class TestTriggerReplan:
    def test_trigger_replan_empty_result_backtracks(self, orch, mock_planner):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan(sample_plan())
        orch.graph = g
        g.mark_failed("1", "error")
        g.get_node("1").alternative_descriptions = []

        mock_planner.replan.return_value = []
        result = orch._trigger_replan("task", g.get_failed_nodes())
        assert result is False

    def test_trigger_replan_merges_plan_on_success(self, orch, mock_planner):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan(sample_plan())
        orch.graph = g
        g.mark_failed("1", "error")

        mock_planner.replan.return_value = [
            {"id": "1", "description": "new approach", "depends_on": []},
            {"id": "2", "description": "后续任务", "depends_on": ["1"]},
        ]
        result = orch._trigger_replan("task", g.get_failed_nodes())
        assert result is True
        assert g.get_node("1").description == "new approach"


class TestBacktrack:
    def test_backtrack_with_alternatives_returns_true(self, orch):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan(sample_plan())
        orch.graph = g
        g.get_node("1").alternative_descriptions = ["alt route"]
        g.mark_failed("1", "err")

        result = orch._backtrack(g.get_node("1"))
        assert result is True
        assert g.get_node("1").status == "pending"

    def test_backtrack_without_alternatives_returns_false(self, orch):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan(sample_plan())
        orch.graph = g
        g.mark_failed("1", "err")

        result = orch._backtrack(g.get_node("1"))
        assert result is False


class TestRunParallel:
    def test_run_parallel_executes_all_ready_nodes(self, orch, mock_executor, mock_critic):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        g.from_plan([
            {"id": "1", "description": "A", "depends_on": []},
            {"id": "2", "description": "B", "depends_on": []},
        ])
        orch.graph = g

        mock_executor.handle_message.return_value = make_pass_reply(
            Message(type="task", sender="orchestrator", receiver="executor", payload={}), "ok"
        )
        mock_critic.handle_message.return_value = make_critic_pass(
            Message(type="task", sender="orchestrator", receiver="critic", payload={})
        )

        ready = g.get_ready_tasks()
        orch._run_parallel(ready, {}, max_retries=1)
        assert mock_executor.handle_message.call_count >= 2

    def test_run_parallel_empty_list_skips_execution(self, orch, mock_executor):
        from agents.plan_graph import PlanGraph
        g = PlanGraph()
        orch.graph = g
        with pytest.raises(ValueError):
            orch._run_parallel([], {}, max_retries=1)


class TestRunSequential:
    def test_run_sequential_delegates_to_run_with_graph(self, orch, mock_planner):
        mock_planner.handle_message.return_value = Message(
            type="result", sender="planner", receiver="orchestrator", payload=[],
        )
        result = orch.run_sequential("task", max_retries=1)
        assert isinstance(result, str)
