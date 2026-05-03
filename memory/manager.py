from memory.store import JSONMemoryStore, MemoryStore
from typing import List, Optional
import time

class MemoryManager:
    def __init__(self, store: MemoryStore = None): # type: ignore
        self.store = store or JSONMemoryStore()
        
    def add_from_tool_result(self, task: str, tool_name: str, input: str, output: str):
        """记录工具调用经验"""
        content = f"工具{tool_name}成功执行, 输入：{input}，输出：{output}"
        self.store.add({
            "type": "tool_result",
            "content": content,
            "task": task,
            "tags": self._extract_tags(task + " " + tool_name),
            "importance": 0.3  # 默认工具调用重要性稍低
        })
        
    def add_reflection_insight(self, task: str, feedback: str):
        """记录反思反馈中的教训"""
        content = f"反思记录: {feedback}"
        self.store.add({
            "type": "reflection",
            "content": content,
            "task": task,
            "tags": self._extract_tags(task),
            "importance": 0.7  # 反思得到的教训很重要
        })
        
    def add_user_preference(self, preference: str):
        """记录用户偏好（长期）"""
        self.store.add({
            "type": "user_preference",
            "content": preference,
            "task": "",
            "tags": self._extract_tags(preference),
            "importance": 0.9
        })
        
    def retrieve_relevant(self, task: str, top_k: int = 3) -> List[str]:
        """检索相关记忆，返回文本列表"""
        memories = self.store.search(task, top_k=top_k)
        # 更新访问计数和时间
        for mem in memories:
            self.store.update(mem["id"], {
                "access_count": mem.get("access_count", 0) + 1,
                "last_accessed": time.time()
            })
        return [mem["content"] for mem in memories]
    
    def _extract_tags(self, text: str) -> List[str]:
        """简单提取关键词作为标签（可替换为 LLM 或 NLP 库）"""
        import re
        # 提取中文词和英文单词
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
        # 简单去重并过滤长度
        return list(set([w for w in words if len(w) > 1]))[:10]
    
    def compress(self, max_items=100, importance_threshold=0.2, days=7):
        """压缩记忆：仅保留重要性高或近期访问的条目"""
        all_momories = self.store.get_all()
        now = time.time()
        kept = []
        for mem in all_momories:
            age_days = (now - mem.get("timestamp", 0)) / 86400
            # 保留规则：重要性高、近期访问、新近创建
            if (mem.get("importance", 0) > importance_threshold or
            (mem.get("last_accessed") and (now - mem["last_accessed"]) / 86400 < days) or
            age_days < 1):
                kept.append(mem)
                
         # 按重要性排序，保留 top max_items
        kept.sort(key=lambda x: x.get("importance", 0), reverse=True)
        kept = kept[:max_items]
        # 重新保存
        self.store.replace_all(kept)