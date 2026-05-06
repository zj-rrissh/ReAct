"""JSONMemoryStore 测试 (22 用例)。"""

import json
import os
import time

import pytest
from memory.store import MemoryStore, JSONMemoryStore


class TestMemoryStoreABC:
    def test_memory_store_is_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            MemoryStore()


class TestJSONMemoryStore:
    def test_init_creates_file(self, temp_memory_file):
        store = JSONMemoryStore(filepath=temp_memory_file)
        assert os.path.exists(temp_memory_file)
        with open(temp_memory_file) as f:
            data = json.load(f)
        assert data == []

    def test_init_creates_parent_directory(self, tmp_path):
        filepath = str(tmp_path / "deep" / "nested" / "memories.json")
        store = JSONMemoryStore(filepath=filepath)
        assert os.path.exists(filepath)

    def test_init_with_existing_file_does_not_overwrite(self, temp_memory_file):
        with open(temp_memory_file, "w") as f:
            json.dump([{"existing": True}], f)
        store = JSONMemoryStore(filepath=temp_memory_file)
        data = store.get_all()
        assert len(data) == 1
        assert data[0]["existing"] is True

    def test_add_returns_id_string(self, json_memory_store):
        mid = json_memory_store.add({"type": "test", "content": "hello"})
        assert isinstance(mid, str)
        assert len(mid) == 8

    def test_add_creates_unique_ids(self, json_memory_store):
        ids = set()
        for _ in range(10):
            ids.add(json_memory_store.add({"content": "test"}))
        assert len(ids) == 10

    def test_add_sets_default_fields(self, json_memory_store):
        mid = json_memory_store.add({"type": "test", "content": "hello"})
        mem = json_memory_store.get_by_id(mid)
        assert "timestamp" in mem
        assert mem["importance"] == 0.5
        assert mem["access_count"] == 0
        assert mem["last_accessed"] is None

    def test_add_preserves_existing_fields(self, json_memory_store):
        mid = json_memory_store.add({
            "type": "test",
            "content": "hello",
            "importance": 0.8,
            "custom_field": "custom_value",
        })
        mem = json_memory_store.get_by_id(mid)
        assert mem["importance"] == 0.8
        assert mem["custom_field"] == "custom_value"

    def test_get_by_id_returns_memory(self, json_memory_store):
        mid = json_memory_store.add({"content": "find me"})
        mem = json_memory_store.get_by_id(mid)
        assert mem is not None
        assert mem["content"] == "find me"

    def test_get_by_id_nonexistent_returns_none(self, json_memory_store):
        assert json_memory_store.get_by_id("nonexistent") is None

    def test_search_matches_keywords(self, populated_store):
        results = populated_store.search("搜索 量子")
        assert len(results) > 0
        assert any(
            "量子" in mem.get("content", "") or "量子" in " ".join(mem.get("tags", []))
            for mem in results
        )

    def test_search_respects_top_k(self, populated_store):
        for i in range(10):
            populated_store.add({"content": f"test {i}", "tags": ["test"]})
        results = populated_store.search("test", top_k=3)
        assert len(results) <= 3

    def test_search_no_match_returns_empty(self, populated_store):
        results = populated_store.search("xyznonexistentword")
        assert results == []

    def test_search_matches_tags(self, populated_store):
        results = populated_store.search("calculator")
        assert len(results) > 0

    def test_search_case_insensitive(self, populated_store):
        results_lower = populated_store.search("calculator")
        results_upper = populated_store.search("CALCULATOR")
        assert len(results_lower) == len(results_upper)

    def test_search_with_chinese_keywords(self, populated_store):
        results = populated_store.search("量子 计算")
        assert len(results) > 0

    def test_update_modifies_existing_memory(self, json_memory_store):
        mid = json_memory_store.add({"content": "old", "importance": 0.5})
        json_memory_store.update(mid, {"content": "new", "importance": 0.9})
        mem = json_memory_store.get_by_id(mid)
        assert mem["content"] == "new"
        assert mem["importance"] == 0.9

    def test_update_nonexistent_does_nothing(self, json_memory_store):
        json_memory_store.update("nonexistent", {"content": "new"})
        assert json_memory_store.get_by_id("nonexistent") is None

    def test_delete_removes_memory(self, json_memory_store):
        mid = json_memory_store.add({"content": "delete me"})
        json_memory_store.delete(mid)
        assert json_memory_store.get_by_id(mid) is None

    def test_delete_nonexistent_does_nothing(self, json_memory_store):
        json_memory_store.delete("nonexistent")
        assert json_memory_store.get_all() == []

    def test_get_all_returns_all_memories(self, populated_store):
        all_mem = populated_store.get_all()
        assert len(all_mem) == 4

    def test_replace_all_replaces_everything(self, populated_store):
        new_data = [{"content": "only me", "type": "test"}]
        populated_store.replace_all(new_data)
        all_mem = populated_store.get_all()
        assert len(all_mem) == 1
        assert all_mem[0]["content"] == "only me"

    def test_persistence_across_instances(self, temp_memory_file):
        store1 = JSONMemoryStore(filepath=temp_memory_file)
        mid = store1.add({"content": "persistent"})

        store2 = JSONMemoryStore(filepath=temp_memory_file)
        mem = store2.get_by_id(mid)
        assert mem is not None
        assert mem["content"] == "persistent"
