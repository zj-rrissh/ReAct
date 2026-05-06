"""ReAct.py CLI 入口集成测试 (16 用例)。"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 导入被测函数
from ReAct import (
    create_client,
    create_deepseek_client,
    create_ollama_client,
    create_orchestrator,
    handle_command,
)
from utils.llm_client import LLMClient


# ── create_client ──

class TestCreateClient:
    def test_create_client_deepseek_returns_llm_client(self, set_deepseek_env):
        with patch("ReAct.create_deepseek_client") as mock_create:
            mock_create.return_value = MagicMock(spec=LLMClient)
            client = create_client("deepseek", "deepseek-chat")
            assert isinstance(client, MagicMock)

    def test_create_client_ollama_returns_llm_client(self):
        with patch("ReAct.create_ollama_client") as mock_create:
            mock_create.return_value = MagicMock(spec=LLMClient)
            client = create_client("ollama", "llama3:8b")
            assert isinstance(client, MagicMock)

    def test_create_client_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="未知"):
            create_client("unknown", "model")


# ── create_deepseek_client ──

class TestCreateDeepseekClient:
    def test_create_deepseek_client_no_api_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            create_deepseek_client()

    def test_create_deepseek_client_with_api_key(self, set_deepseek_env):
        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "test response"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)
        with patch.dict("sys.modules", {"openai": fake_openai}):
            client = create_deepseek_client("deepseek-chat")
            assert isinstance(client, LLMClient)
            result = client.generate("hello")
            assert result == "test response"


# ── create_ollama_client ──

class TestCreateOllamaClient:
    def test_create_ollama_client_returns_llm_client(self):
        fake_ollama = MagicMock()
        fake_ollama.chat.return_value = {"message": {"content": "ollama reply"}}
        with patch.dict("sys.modules", {"ollama": fake_ollama}):
            client = create_ollama_client("llama3:8b")
            assert isinstance(client, LLMClient)
            result = client.generate("hello")
            assert result == "ollama reply"


# ── create_orchestrator ──

class TestCreateOrchestrator:
    def test_create_orchestrator_returns_orchestrator_and_memory(self, set_deepseek_env):
        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "test"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)
        with patch.dict("sys.modules", {"openai": fake_openai}):
            llm_client = create_deepseek_client("deepseek-chat")
            orch, memory = create_orchestrator("deepseek-chat", llm_client)
            assert orch is not None
            assert memory is not None

    def test_create_orchestrator_components_have_correct_types(self, set_deepseek_env):
        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "test"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)
        from agents.orchestrator import Orchestrator
        from memory.manager import MemoryManager
        with patch.dict("sys.modules", {"openai": fake_openai}):
            llm_client = create_deepseek_client("deepseek-chat")
            orch, memory = create_orchestrator("deepseek-chat", llm_client)
            assert isinstance(orch, Orchestrator)
            assert isinstance(memory, MemoryManager)


# ── handle_command ──

class TestHandleCommand:
    @pytest.fixture
    def state(self):
        return {
            "reflect_on": False,
            "orchestrate_on": False,
            "orchestrator": None,
            "llm_client": MagicMock(),
            "model_name": "test-model",
            "agent": MagicMock(),
            "max_retries": 2,
            "max_steps": 20,
            "parallel": False,
            "max_replans": 2,
        }

    def test_handle_reflect_on(self, state):
        handle_command("/reflect on", state)
        assert state["reflect_on"] is True

    def test_handle_reflect_off(self, state):
        state["reflect_on"] = True
        handle_command("/reflect off", state)
        assert state["reflect_on"] is False

    def test_handle_reflect_toggle(self, state):
        handle_command("/reflect", state)
        assert state["reflect_on"] is True
        handle_command("/reflect", state)
        assert state["reflect_on"] is False

    def test_handle_reflect_blocked_when_orchestrate_on(self, state):
        state["orchestrate_on"] = True
        handle_command("/reflect on", state)
        assert state["reflect_on"] is False

    def test_handle_orch_on(self, state):
        with patch("ReAct.create_orchestrator") as mock_co:
            mock_co.return_value = (MagicMock(), MagicMock())
            handle_command("/orch on", state)
            assert state["orchestrate_on"] is True

    def test_handle_orch_off(self, state):
        state["orchestrate_on"] = True
        state["orchestrator"] = MagicMock()
        handle_command("/orch off", state)
        assert state["orchestrate_on"] is False
        assert state["orchestrator"] is None

    def test_handle_orch_toggle(self, state):
        with patch("ReAct.create_orchestrator") as mock_co:
            mock_co.return_value = (MagicMock(), MagicMock())
            handle_command("/orch", state)
            assert state["orchestrate_on"] is True
            handle_command("/orch", state)
            assert state["orchestrate_on"] is False

    def test_handle_orch_turns_off_reflect(self, state):
        state["reflect_on"] = True
        with patch("ReAct.create_orchestrator") as mock_co:
            mock_co.return_value = (MagicMock(), MagicMock())
            handle_command("/orch on", state)
            assert state["reflect_on"] is False

    def test_handle_help(self, state):
        handle_command("/help", state)

    def test_handle_unknown_command(self, state):
        handle_command("/foo", state)
