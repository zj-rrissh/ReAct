"""config.json 加载逻辑测试。"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from ReAct import load_config


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        """正常加载合法 config.json。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "openai",
            "model": "gpt-4o",
            "providers": {
                "openai": {
                    "type": "openai_compatible",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "",
                    "api_key_env": "OPENAI_API_KEY"
                }
            }
        }))
        config = load_config(str(config_path))
        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o"
        assert "openai" in config["providers"]

    def test_load_config_default_path(self, tmp_path, monkeypatch):
        """无参数时从当前目录加载 config.json。"""
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
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config["provider"] == "deepseek"

    def test_missing_config_raises_file_not_found(self, tmp_path):
        """config.json 不存在时抛出 FileNotFoundError，包含示例内容。"""
        missing_path = str(tmp_path / "config.json")
        with pytest.raises(FileNotFoundError, match="config.json"):
            load_config(missing_path)

    def test_invalid_json_raises_value_error(self, tmp_path):
        """config.json 格式错误时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text("{ invalid json }")
        with pytest.raises(ValueError, match="JSON"):
            load_config(str(config_path))

    def test_missing_provider_field_raises_value_error(self, tmp_path):
        """config.json 缺少 provider 字段时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "model": "gpt-4o",
            "providers": {}
        }))
        with pytest.raises(ValueError, match="provider"):
            load_config(str(config_path))

    def test_missing_providers_field_raises_value_error(self, tmp_path):
        """config.json 缺少 providers 字段时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "deepseek",
            "model": "deepseek-chat"
        }))
        with pytest.raises(ValueError, match="providers"):
            load_config(str(config_path))

    def test_missing_model_defaults_to_provider(self, tmp_path):
        """config.json 缺少 model 字段时自动使用 provider 名称。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "my_llm",
            "providers": {
                "my_llm": {
                    "type": "openai_compatible",
                    "base_url": "https://api.example.com",
                    "api_key": "sk-test",
                    "api_key_env": "MY_KEY"
                }
            }
        }))
        config = load_config(str(config_path))
        assert config["model"] == "my_llm"

    def test_provider_not_in_providers_raises_value_error(self, tmp_path):
        """provider 不在 providers 列表中时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "unknown",
            "model": "some-model",
            "providers": {
                "deepseek": {"type": "openai_compatible", "base_url": "https://api.deepseek.com", "api_key": "", "api_key_env": "DEEPSEEK_API_KEY"}
            }
        }))
        with pytest.raises(ValueError, match="unknown"):
            load_config(str(config_path))
