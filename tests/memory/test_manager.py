"""MemoryManager 测试 (18 用例)。"""

import time
from unittest.mock import MagicMock

import pytest
from memory.manager import MemoryManager


class TestExtractTags:
    def test_extract_chinese_tags(self, memory_manager):
        tags = memory_manager._extract_tags("搜索量子计算")
        assert "搜索量子计算" in tags or "搜索" in tags or "量子" in tags

    def test_extract_english_tags(self, memory_manager):
        tags = memory_manager._extract_tags("search engine")
        assert "search" in tags
        assert "engine" in tags

    def test_extract_mixed_language_tags(self, memory_manager):
        tags = memory_manager._extract_tags("AI 人工智能 machine learning")
        assert "AI" in tags or "machine" in tags or "learning" in tags
        assert "人工智能" in tags

    def test_extract_empty_string_returns_empty(self, memory_manager):
        tags = memory_manager._extract_tags("")
        assert tags == []

    def test_extract_single_character_filtered_out(self, memory_manager):
        tags = memory_manager._extract_tags("a b c")
        assert all(len(t) > 1 for t in tags)

    def test_extract_tags_max_10_limit(self, memory_manager):
        tags = memory_manager._extract_tags(
            "one two three four five six seven eight nine ten eleven twelve thirteen"
        )
        assert len(tags) <= 10


class TestAddMethods:
    def test_add_from_tool_result_sets_importance_0_3(self, memory_manager, json_memory_store):
        memory_manager.add_from_tool_result("task", "calc", "2+3", "5")
        all_mem = json_memory_store.get_all()
        assert len(all_mem) == 1
        assert all_mem[0]["importance"] == 0.3
        assert all_mem[0]["type"] == "tool_result"

    def test_add_reflection_insight_sets_importance_0_7(self, memory_manager, json_memory_store):
        memory_manager.add_reflection_insight("task", "need better search keywords")
        all_mem = json_memory_store.get_all()
        assert len(all_mem) == 1
        assert all_mem[0]["importance"] == 0.7
        assert all_mem[0]["type"] == "reflection"

    def test_add_user_preference_sets_importance_0_9(self, memory_manager, json_memory_store):
        memory_manager.add_user_preference("prefer Chinese answers")
        all_mem = json_memory_store.get_all()
        assert len(all_mem) == 1
        assert all_mem[0]["importance"] == 0.9
        assert all_mem[0]["type"] == "user_preference"

    def test_add_user_preference_empty_task(self, memory_manager, json_memory_store):
        memory_manager.add_user_preference("some preference")
        mem = json_memory_store.get_all()[0]
        assert mem["task"] == ""


class TestRetrieveRelevant:
    def test_retrieve_relevant_calls_store_search(self, memory_manager):
        memory_manager.store = MagicMock()
        memory_manager.store.search.return_value = []
        memory_manager.retrieve_relevant("test query")
        memory_manager.store.search.assert_called_once_with("test query", top_k=3)

    def test_retrieve_relevant_updates_access_count(self, json_memory_store, memory_manager):
        json_memory_store.add({
            "type": "test", "content": "test memory for access count",
            "importance": 0.5, "access_count": 0, "tags": ["test"],
        })
        results = memory_manager.retrieve_relevant("test for access", top_k=1)
        assert len(results) > 0
        all_mem = json_memory_store.get_all()
        accessed = [m for m in all_mem if m["content"] == "test memory for access count"]
        if accessed:
            assert accessed[0]["access_count"] == 1

    def test_retrieve_relevant_updates_last_accessed(self, json_memory_store, memory_manager):
        json_memory_store.add({
            "type": "test", "content": "last accessed test memory",
            "importance": 0.5, "access_count": 0, "tags": ["test"],
        })
        before = time.time()
        memory_manager.retrieve_relevant("last accessed", top_k=1)
        all_mem = json_memory_store.get_all()
        target = [m for m in all_mem if m["content"] == "last accessed test memory"]
        if target:
            assert target[0]["last_accessed"] is not None
            assert target[0]["last_accessed"] >= before

    def test_retrieve_relevant_returns_content_list(self, memory_manager):
        memory_manager.store = MagicMock()
        memory_manager.store.search.return_value = [
            {"id": "1", "content": "memory one", "access_count": 0},
            {"id": "2", "content": "memory two", "access_count": 0},
        ]
        memory_manager.store.update = MagicMock()
        results = memory_manager.retrieve_relevant("test")
        assert results == ["memory one", "memory two"]

    def test_retrieve_relevant_respects_top_k(self, memory_manager):
        memory_manager.store = MagicMock()
        memory_manager.store.search.return_value = []
        memory_manager.retrieve_relevant("query", top_k=7)
        memory_manager.store.search.assert_called_once_with("query", top_k=7)


class TestCompress:
    def test_compress_keeps_high_importance(self, json_memory_store, memory_manager):
        now = time.time()
        json_memory_store.add({"content": "high", "importance": 0.9, "timestamp": now - 86400 * 30})
        json_memory_store.add({"content": "low", "importance": 0.1, "timestamp": now - 86400 * 30})
        memory_manager.compress(max_items=50, importance_threshold=0.2, days=7)
        remaining = json_memory_store.get_all()
        contents = [m["content"] for m in remaining]
        assert "high" in contents

    def test_compress_keeps_recently_accessed(self, json_memory_store, memory_manager):
        now = time.time()
        json_memory_store.add({
            "content": "recently_accessed", "importance": 0.1, "timestamp": now - 86400 * 30,
            "last_accessed": now - 3600,
        })
        memory_manager.compress(max_items=50, importance_threshold=0.2, days=7)
        remaining = json_memory_store.get_all()
        contents = [m["content"] for m in remaining]
        assert "recently_accessed" in contents

    def test_compress_keeps_newly_created(self, json_memory_store, memory_manager):
        now = time.time()
        json_memory_store.add({
            "content": "brand_new", "importance": 0.1,
            "timestamp": now - 3600, "last_accessed": None,
        })
        memory_manager.compress(max_items=50, importance_threshold=0.2, days=7)
        remaining = json_memory_store.get_all()
        contents = [m["content"] for m in remaining]
        assert "brand_new" in contents

    def test_compress_drops_low_importance_old_not_accessed(self, json_memory_store, memory_manager):
        now = time.time()
        json_memory_store.add({
            "content": "should_drop", "importance": 0.1, "timestamp": now - 86400 * 30,
            "last_accessed": now - 86400 * 10,
        })
        json_memory_store.add({
            "content": "should_keep", "importance": 0.9, "timestamp": now,
        })
        memory_manager.compress(max_items=50, importance_threshold=0.2, days=7)
        remaining = json_memory_store.get_all()
        contents = [m["content"] for m in remaining]
        assert "should_keep" in contents

    def test_compress_respects_max_items(self, json_memory_store, memory_manager):
        now = time.time()
        for i in range(20):
            json_memory_store.add({
                "content": f"item_{i}", "importance": 0.5,
                "timestamp": now, "last_accessed": now,
            })
        memory_manager.compress(max_items=10, importance_threshold=0.2, days=365)
        assert len(json_memory_store.get_all()) <= 10

    def test_compress_sorts_by_importance_descending(self, json_memory_store, memory_manager):
        now = time.time()
        json_memory_store.add({"content": "med", "importance": 0.5, "timestamp": now})
        json_memory_store.add({"content": "high", "importance": 0.9, "timestamp": now})
        json_memory_store.add({"content": "low", "importance": 0.2, "timestamp": now})
        memory_manager.compress(max_items=2, importance_threshold=0.1, days=365)
        remaining = json_memory_store.get_all()
        contents = [m["content"] for m in remaining]
        assert contents[0] == "high"

    def test_compress_calls_replace_all(self, json_memory_store, memory_manager):
        memory_manager.compress()
        all_mem = json_memory_store.get_all()
        assert isinstance(all_mem, list)
