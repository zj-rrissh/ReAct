"""SearchTool 测试 (6 用例)。"""

import pytest
from tools.search import SearchTool


@pytest.fixture
def search_tool():
    return SearchTool()


class TestSearchTool:
    def test_search_returns_expected_format(self, search_tool):
        result = search_tool.execute("python")
        assert "python" in result
        assert "搜索结果" in result

    def test_search_contains_input_keyword(self, search_tool):
        result = search_tool.execute("量子计算")
        assert "量子计算" in result

    def test_search_with_chinese_input(self, search_tool):
        result = search_tool.execute("人工智能")
        assert "人工智能" in result
        assert "示例结果" in result

    def test_search_with_empty_string(self, search_tool):
        result = search_tool.execute("")
        assert "搜索结果" in result

    def test_search_tool_has_correct_name(self, search_tool):
        assert search_tool.name == "search"

    def test_search_tool_has_description(self, search_tool):
        assert search_tool.description
        assert "搜索" in search_tool.description
