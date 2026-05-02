from typing import ClassVar

from tools.base import Tool
import os
from tools.registry import register_tool

ALLOWED_BASE = os.path.abspath("./workspace") # 只有这个目录下的文件可读

@register_tool(name="file_read")
class FileReadTool(Tool):
    name: ClassVar[str] = "file_read"
    description: ClassVar[str] = ("读取指定路径的文件内容，输入相对路径（相对于工作区 './workspace'），"
        "返回文件文本内容。")

    def execute(self, input: str) -> str:
        filepath = input.strip().strip("'\"").strip()
        full_path = os.path.join(ALLOWED_BASE, filepath)
        full_path = os.path.abspath(full_path)   # 防止路径穿越
        if not full_path.startswith(ALLOWED_BASE):
            return "错误: 不允许访问工作区外的路径"
        if not os.path.exists(full_path):
            return f"错误: 文件不存在: {filepath}"
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            return f"读取文件失败: {str(e)}"