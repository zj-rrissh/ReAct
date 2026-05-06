"""ReAct.py CLI 入口集成测试 (16 用例)。"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 导入被测函数
from ReAct import (
    create_client,
    create_openai_compatible_client,
    create_ollama_client,
    create_orchestrator,
    handle_command,
)
from utils.llm_client import LLMClient


# ── create_client ──

class TestCreateClient:
    def test_create_client_from_config_deepseek(self, tmp_path, monkeypatch):
        """从 config 读取 deepseek provider 创建客户端。"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "deepseek",
            "model": "deepseek-chat",
            "providers": {
                "deepseek": {
                    "type": "openai_compatible",
                    "base_url": "https://api.deepseek.com",
                    "api_key": "",
                    "api_key_env": "DEEPSEEK_API_KEY"
                }
            }
        }))
        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "test"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)
        with patch.dict("sys.modules", {"openai": fake_openai}):
            client = create_client(config_path=str(config_path))
            assert isinstance(client, LLMClient)

    def test_create_client_from_config_ollama(self, tmp_path):
        """从 config 读取 ollama provider 创建客户端。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "ollama",
            "model": "llama3:8b",
            "providers": {
                "ollama": {
                    "type": "ollama",
                    "model": "llama3:8b"
                }
            }
        }))
        fake_ollama = MagicMock()
        fake_ollama.chat.return_value = {"message": {"content": "reply"}}
        with patch.dict("sys.modules", {"ollama": fake_ollama}):
            client = create_client(config_path=str(config_path))
            assert isinstance(client, LLMClient)

    def test_create_client_unknown_provider_type_raises_value_error(self, tmp_path):
        """config 中 provider type 未知时报错。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "bad",
            "model": "bad-model",
            "providers": {
                "bad": {
                    "type": "unknown_type"
                }
            }
        }))
        with pytest.raises(ValueError, match="type"):
            create_client(config_path=str(config_path))


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
            llm_client = create_openai_compatible_client(
                provider_name="deepseek",
                model_name="deepseek-chat",
                base_url="https://api.deepseek.com",
                api_key="",
                api_key_env="DEEPSEEK_API_KEY",
            )
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
            llm_client = create_openai_compatible_client(
                provider_name="deepseek",
                model_name="deepseek-chat",
                base_url="https://api.deepseek.com",
                api_key="",
                api_key_env="DEEPSEEK_API_KEY",
            )
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

    def test_handle_parallel_toggle(self, state):
        handle_command("/parallel", state)
        assert state["parallel"] is True
        handle_command("/parallel", state)
        assert state["parallel"] is False

    def test_handle_parallel_on_off(self, state):
        handle_command("/parallel on", state)
        assert state["parallel"] is True
        handle_command("/parallel off", state)
        assert state["parallel"] is False

    def test_handle_parallel_short_form(self, state):
        handle_command("/pl on", state)
        assert state["parallel"] is True

    def test_handle_replans_set(self, state):
        handle_command("/replans 5", state)
        assert state["max_replans"] == 5

    def test_handle_replans_show(self, state):
        state["max_replans"] = 3
        handle_command("/replans", state)
        assert state["max_replans"] == 3

    def test_handle_replans_short_form(self, state):
        handle_command("/rp 4", state)
        assert state["max_replans"] == 4

    def test_handle_help(self, state):
        handle_command("/help", state)

    def test_handle_unknown_command(self, state):
        handle_command("/foo", state)
