"""config.json 端到端集成测试。"""
import json
import os

import pytest


class TestConfigIntegration:
    """完整的 config.json -> create_client -> LLMClient 流程测试。"""

    def test_full_flow_openai_compatible(self, tmp_path, monkeypatch):
        """完整流程: config.json 定义 openai_compatible -> 创建客户端 -> 调用 LLM。"""
        from unittest.mock import MagicMock, patch

        monkeypatch.setenv("MY_KEY", "sk-integration-test")

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "my_provider",
            "model": "my-model-v1",
            "providers": {
                "my_provider": {
                    "type": "openai_compatible",
                    "base_url": "https://my-api.example.com",
                    "api_key": "",
                    "api_key_env": "MY_KEY"
                }
            }
        }))

        from ReAct import create_client

        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "integration response"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)

        with patch.dict("sys.modules", {"openai": fake_openai}):
            from ReAct import create_client
            client = create_client(config_path=str(config_path))
            result = client.generate("hello")
            assert result == "integration response"

    def test_full_flow_config_api_key_fallback(self, tmp_path, monkeypatch):
        """config.json 中直接写 api_key，无环境变量时的完整流程。"""
        from unittest.mock import MagicMock, patch

        monkeypatch.delenv("MY_OTHER_KEY", raising=False)

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "test_p",
            "model": "test-m",
            "providers": {
                "test_p": {
                    "type": "openai_compatible",
                    "base_url": "https://test.example.com",
                    "api_key": "sk-direct-key",
                    "api_key_env": "MY_OTHER_KEY"
                }
            }
        }))

        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "direct key response"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)

        with patch.dict("sys.modules", {"openai": fake_openai}):
            from ReAct import create_client
            client = create_client(config_path=str(config_path))
            result = client.generate("hello")
            assert result == "direct key response"

    def test_cli_override_provider(self, tmp_path, monkeypatch):
        """命令行 --provider 覆盖 config.json 中的 provider。"""
        from unittest.mock import MagicMock, patch

        monkeypatch.setenv("OVERRIDE_KEY", "sk-override")

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "default_p",
            "model": "default-m",
            "providers": {
                "default_p": {
                    "type": "openai_compatible",
                    "base_url": "https://default.example.com",
                    "api_key": "",
                    "api_key_env": "DEFAULT_KEY"
                },
                "override_p": {
                    "type": "openai_compatible",
                    "base_url": "https://override.example.com",
                    "api_key": "",
                    "api_key_env": "OVERRIDE_KEY"
                }
            }
        }))

        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "override"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)

        with patch.dict("sys.modules", {"openai": fake_openai}):
            from ReAct import create_client
            # 使用 provider= 参数覆盖
            client = create_client(config_path=str(config_path), provider="override_p")
            result = client.generate("hello")
            assert result == "override"
