"""ReviewerAgent 测试 (13 用例)。"""

from unittest.mock import MagicMock
import pytest
from agents.reviewer import ReviewerAgent
from agents.message import Message


def make_review_response(decision, feedback):
    """构造 Reviewer LLM 的标准响应格式。"""
    return f"Decision: {decision}\nFeedback: {feedback}"


class TestReview:
    def test_review_pass_returns_true(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_review_response("PASS", "无"))
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.review("task", "answer")
        assert passed is True

    def test_review_fail_returns_false(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_review_response("FAIL", "不够完整"))
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.review("task", "answer")
        assert passed is False

    def test_review_extracts_feedback_correctly(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_review_response("FAIL", "需要更多细节"))
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.review("task", "answer")
        assert feedback == "需要更多细节"

    def test_review_no_feedback_line_returns_full_response(self, mock_llm_client):
        response = "Decision: FAIL\nSome notes without proper format"
        mock_llm_client.generate = MagicMock(return_value=response)
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.review("task", "answer")
        assert passed is False
        assert "Some notes" in feedback

    def test_review_decision_line_not_present_defaults_fail(self, mock_llm_client):
        response = "Feedback: 内容不够好"
        mock_llm_client.generate = MagicMock(return_value=response)
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent.review("task", "answer")
        assert passed is False


class TestParseReview:
    def test_parse_review_decision_pass_in_line(self, mock_llm_client):
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, _ = agent._parse_review(make_review_response("PASS", "无"))
        assert passed is True

    def test_parse_review_decision_fail_in_line(self, mock_llm_client):
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, _ = agent._parse_review(make_review_response("FAIL", "需要改进"))
        assert passed is False

    def test_parse_review_pass_not_confused_by_feedback_text(self, mock_llm_client):
        response = "Decision: FAIL\nFeedback: pass 出现次数不够，需要更多分析"
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, feedback = agent._parse_review(response)
        assert passed is False

    def test_parse_review_no_decision_line_returns_false(self, mock_llm_client):
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        passed, _ = agent._parse_review("只有 feedback 没有 decision")
        assert passed is False

    def test_parse_review_extracts_feedback_after_colon(self, mock_llm_client):
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        _, feedback = agent._parse_review(make_review_response("FAIL", "具体改进建议"))
        assert feedback == "具体改进建议"

    def test_parse_review_no_feedback_line_returns_entire_response(self, mock_llm_client):
        response = "Decision: PASS"
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        _, feedback = agent._parse_review(response)
        assert feedback == "Decision: PASS"


class TestHandleMessage:
    def test_handle_message_pass_response(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_review_response("PASS", "无"))
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        msg = Message(type="task", sender="orchestrator", receiver="reviewer",
                      payload={"task": "test task", "answer": "test answer"})
        reply = agent.handle_message(msg)
        assert reply.type == "feedback"
        assert reply.sender == "reviewer"
        assert reply.receiver == "orchestrator"
        assert reply.payload["passed"] is True

    def test_handle_message_fail_response(self, mock_llm_client):
        mock_llm_client.generate = MagicMock(return_value=make_review_response("FAIL", "不够好"))
        agent = ReviewerAgent(model_name="test", llm_client=mock_llm_client)
        msg = Message(type="task", sender="orchestrator", receiver="reviewer",
                      payload={"task": "test task", "answer": "test answer"})
        reply = agent.handle_message(msg)
        assert reply.payload["passed"] is False
        assert reply.payload["feedback"] == "不够好"
