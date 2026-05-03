# memory/store.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import json, os, uuid, time

class MemoryStore(ABC):
    @abstractmethod
    def add(self, memory: dict) -> str:
        """添加记忆，返回 id"""
        ...

    @abstractmethod
    def get_by_id(self, memory_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """基于查询返回相关记忆列表"""
        ...

    @abstractmethod
    def update(self, memory_id: str, updates: dict) -> None:
        ...

    @abstractmethod
    def delete(self, memory_id: str) -> None:
        ...

    @abstractmethod
    def get_all(self) -> List[dict]:
        ...

    @abstractmethod
    def replace_all(self, memories: List[dict]) -> None:
        """用新列表替换全部记忆"""
        ...


class JSONMemoryStore(MemoryStore):
    def __init__(self, filepath="memory/memories.json"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _load(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, memory: dict) -> str:
        data = self._load()
        memory["id"] = str(uuid.uuid4())[:8]
        memory.setdefault("timestamp", time.time())
        memory.setdefault("importance", 0.5)
        memory.setdefault("access_count", 0)
        memory.setdefault("last_accessed", None)
        data.append(memory)
        self._save(data)
        return memory["id"]

    def get_by_id(self, memory_id: str) -> Optional[dict]:
        data = self._load()
        for mem in data:
            if mem["id"] == memory_id:
                return mem
        return None

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        data = self._load()
        # 极其简单的关键词匹配（仅演示，实际可替换为嵌入向量）
        query_words = set(query.lower().split())
        scored = []
        for mem in data:
            content_lower = mem.get("content", "").lower()
            tags = " ".join(mem.get("tags", []))
            text = content_lower + " " + tags.lower()
            # 计算简单匹配分数
            score = sum(1 for w in query_words if w in text)
            if score > 0:
                scored.append((score, mem))
        # 按分数降序，取 top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:top_k]]

    def update(self, memory_id: str, updates: dict) -> None:
        data = self._load()
        for mem in data:
            if mem["id"] == memory_id:
                mem.update(updates)
                break
        self._save(data)

    def delete(self, memory_id: str) -> None:
        data = self._load()
        data = [mem for mem in data if mem["id"] != memory_id]
        self._save(data)

    def get_all(self) -> List[dict]:
        return self._load()

    def replace_all(self, memories: List[dict]) -> None:
        self._save(memories)