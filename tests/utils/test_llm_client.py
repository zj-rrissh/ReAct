"""LLMClient 测试 (7 用例)。"""

import pytest
from unittest.mock import MagicMock
from utils.llm_client import LLMClient


class TestLLMClient:
    def test_generate_delegates_to_adapter_with_model_and_prompt(self):
        adapter = MagicMock(return_value="result")
        client = LLMClient(model_name="gpt-4", adapter=adapter)
        client.generate("hello")
        adapter.assert_called_once_with("gpt-4", "hello")

    def test_generate_returns_adapter_result(self):
        adapter = MagicMock(return_value="expected output")
        client = LLMClient(model_name="test", adapter=adapter)
        result = client.generate("prompt")
        assert result == "expected output"

    def test_generate_with_different_model_name(self):
        adapter = MagicMock(return_value="ok")
        client = LLMClient(model_name="claude-3", adapter=adapter)
        client.generate("hi")
        adapter.assert_called_once_with("claude-3", "hi")

    def test_generate_with_empty_prompt(self):
        adapter = MagicMock(return_value="")
        client = LLMClient(model_name="test", adapter=adapter)
        result = client.generate("")
        adapter.assert_called_once_with("test", "")

    def test_adapter_exception_propagates(self):
        adapter = MagicMock(side_effect=RuntimeError("LLM error"))
        client = LLMClient(model_name="test", adapter=adapter)
        with pytest.raises(RuntimeError, match="LLM error"):
            client.generate("prompt")

    def test_llm_client_stores_model_name(self):
        client = LLMClient(model_name="custom-model", adapter=lambda m, p: "ok")
        assert client.model == "custom-model"

    def test_llm_client_stores_adapter(self):
        def my_adapter(m, p):
            return "ok"
        client = LLMClient(model_name="test", adapter=my_adapter)
        assert client.adapter is my_adapter
