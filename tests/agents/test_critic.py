"""CriticAgent 测试 (10 用例) —— 含已知 Bug 验证。"""

from unittest.mock import MagicMock
import pytest
from agents.critic import CriticAgent
from agents.message import Message


def make_critic_response(decision, feedback):
    return f"Decision: {decision}\nFeedback: {feedback}"


class TestEvaluate:
    def test_evaluate_pass_returns_true(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_critic_response("PASS", "无"))
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.evaluate("task", "result")
        assert passed is True
        assert feedback == "无"

    def test_evaluate_fail_returns_false(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_critic_response("FAIL", "不完整"))
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.evaluate("task", "result")
        assert passed is False

    def test_evaluate_pass_case_insensitive(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_critic_response("pass", "ok"))
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, _ = agent.evaluate("task", "result")
        assert passed is True

    def test_evaluate_extracts_feedback_correctly(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_critic_response("FAIL", "具体意见"))
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.evaluate("task", "result")
        assert feedback == "具体意见"

    def test_evaluate_no_feedback_line_returns_full_response(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="Decision: FAIL")
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.evaluate("task", "result")
        assert passed is False
        assert "Decision: FAIL" in feedback

    def test_evaluate_pass_in_feedback_but_fail_in_decision(self, mock_llm_client):
        """Feedback 中的 'pass' 不应影响 Decision 行 FAIL 的判定。"""
        response = "Decision: FAIL\nFeedback: 请确保所有 pass 条件已满足"
        mock_llm_client.generate = MagicMock(return_value=response)
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, _ = agent.evaluate("task", "result")
        assert passed is False

    def test_evaluate_default_fail_when_no_decision_keyword(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value="一些随意的评论，没有 Decision")
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, _ = agent.evaluate("task", "result")
        assert passed is False

    def test_evaluate_with_colons_in_feedback_text(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_critic_response("FAIL", "注意: 内容不对"))
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.evaluate("task", "result")
        assert "注意: 内容不对" in feedback


class TestHandleMessage:
    def test_handle_message_pass_contains_passed_true(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_critic_response("PASS", "无"))
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        msg = Message(type="task", sender="orchestrator", receiver="critic",
                      payload={"task": "test", "result": "ok"})
        reply = agent.handle_message(msg)
        assert reply.type == "feedback"
        assert reply.payload["passed"] is True

    def test_handle_message_fail_contains_passed_false(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_critic_response("FAIL", "bad"))
        agent = CriticAgent(model_name="test", llm_client=mock_llm_client)
        msg = Message(type="task", sender="orchestrator", receiver="critic",
                      payload={"task": "test", "result": "bad"})
        reply = agent.handle_message(msg)
        assert reply.payload["passed"] is False
