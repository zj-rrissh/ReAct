"""WebSearchTool 测试 (6 用例)。"""

import pytest
from unittest.mock import MagicMock
from tools.web_search import WebSearchTool


@pytest.fixture
def web_search_tool():
    return WebSearchTool()


class TestWebSearchTool:
    def test_search_returns_formatted_results(self, web_search_tool, mock_ddgs):
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {"title": "Test Title", "href": "https://example.com", "body": "Result body"},
        ]
        mock_ddgs.return_value = mock_instance

        result = web_search_tool.execute("test query")
        assert "Test Title" in result
        assert "https://example.com" in result
        assert "Result body" in result

    def test_search_no_results_returns_not_found(self, web_search_tool, mock_ddgs):
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.text.return_value = []
        mock_ddgs.return_value = mock_instance

        result = web_search_tool.execute("no results query")
        assert "未找到" in result

    def test_search_exception_returns_error_message(self, web_search_tool, mock_ddgs):
        mock_ddgs.side_effect = Exception("Network error")

        result = web_search_tool.execute("error query")
        assert "搜索失败" in result
        assert "Network error" in result

    def test_search_results_limited_to_5(self, web_search_tool, mock_ddgs):
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {"title": f"T{i}", "href": f"http://e{i}.com", "body": f"Body{i}"}
            for i in range(10)
        ]
        mock_ddgs.return_value = mock_instance

        web_search_tool.execute("query")
        mock_instance.text.assert_called_once_with("query", max_results=5)

    def test_search_result_format_contains_title_link_summary(self, web_search_tool, mock_ddgs):
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {"title": "A", "href": "http://a.com", "body": "body A"},
        ]
        mock_ddgs.return_value = mock_instance

        result = web_search_tool.execute("format test")
        assert "标题:" in result
        assert "链接:" in result
        assert "摘要:" in result

    def test_tool_has_correct_name(self, web_search_tool):
        assert web_search_tool.name == "web_search"
