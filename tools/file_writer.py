import os

from tools.base import Tool, get_workspace_base
from tools.registry import register_tool


@register_tool(name="file_write")
class FileWriteTool(Tool):
    name = "file_write"
    description = (
        "将文本写入指定文件（会覆盖原有内容）。"
        "输入格式: '文件路径 内容'，路径相对于工作区。"
        "例如: 'notes.txt 这是一段笔记'。"
    )

    def execute(self, input: str) -> str:
        allowed_base = get_workspace_base()
        input = input.strip().strip("'").strip('"')
        parts = input.split(" ", 1)
        if len(parts) < 2:
            return "错误: 请提供文件路径和要写入的内容，用空格分隔"
        filepath, content = parts[0], parts[1]

        full_path = os.path.join(allowed_base, filepath)
        full_path = os.path.abspath(full_path)
        if not full_path.startswith(allowed_base):
            return "错误: 不允许写入工作区外的路径"
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"已成功写入文件: {filepath}"
        except Exception as e:
            return f"写入文件失败: {str(e)}"