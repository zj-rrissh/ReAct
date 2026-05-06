"""WikipediaTool 测试 (7 用例)。"""

import pytest
from unittest.mock import MagicMock
from tools.wikipedia import WikipediaTool


@pytest.fixture
def wiki_tool():
    return WikipediaTool()


class TestWikipediaTool:
    def test_search_returns_results_with_snippets(self, wiki_tool, mock_requests_get):
        mock_requests_get.side_effect = [
            self._mock_search_response(["量子计算", "量子力学"]),
            self._mock_extract_response("量子计算", "量子计算是一种利用量子力学原理..."),
        ]

        result = wiki_tool.execute("量子计算")
        assert "量子计算" in result

    def test_search_no_results_returns_not_found(self, wiki_tool, mock_requests_get):
        mock_requests_get.return_value = self._mock_search_response([])

        result = wiki_tool.execute("xyzznonexistent")
        assert "未找到" in result

    def test_search_api_error_returns_error_message(self, wiki_tool, mock_requests_get):
        mock_requests_get.side_effect = Exception("Connection timeout")

        result = wiki_tool.execute("error query")
        assert "维基搜索出错" in result

    def test_search_extract_success(self, wiki_tool, mock_requests_get):
        mock_requests_get.side_effect = [
            self._mock_search_response(["Python"]),
            self._mock_extract_response("Python", "Python is a programming language..."),
        ]

        result = wiki_tool.execute("Python")
        assert "Python" in result

    def test_search_extract_page_not_found(self, wiki_tool, mock_requests_get):
        mock_requests_get.side_effect = [
            self._mock_search_response(["Ghost"]),
            self._mock_extract_response_empty(),
        ]

        result = wiki_tool.execute("Ghost")
        assert "Ghost" in result

    def test_search_result_format(self, wiki_tool, mock_requests_get):
        mock_requests_get.side_effect = [
            self._mock_search_response(["AI"]),
            self._mock_extract_response("AI", "Artificial intelligence..."),
        ]

        result = wiki_tool.execute("AI")
        assert "•" in result
        assert "AI" in result

    def test_tool_has_correct_name(self, wiki_tool):
        assert wiki_tool.name == "wikipedia"

    # ── helpers ──

    @staticmethod
    def _mock_search_response(titles):
        resp = MagicMock()
        resp.json.return_value = {
            "query": {
                "search": [
                    {"title": t, "snippet": f"Snippet for {t}"}
                    for t in titles
                ]
            }
        }
        return resp

    @staticmethod
    def _mock_extract_response(title, extract):
        resp = MagicMock()
        resp.json.return_value = {
            "query": {
                "pages": {
                    "12345": {"title": title, "extract": extract, "pageid": 12345}
                }
            }
        }
        return resp

    @staticmethod
    def _mock_extract_response_empty():
        resp = MagicMock()
        resp.json.return_value = {
            "query": {
                "pages": {
                    "-1": {"title": "Ghost", "missing": ""}
                }
            }
        }
        return resp
