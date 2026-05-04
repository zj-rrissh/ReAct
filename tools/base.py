import os
from abc import abstractmethod, ABC

# --- 工作区配置 ---
_workspace_dir = "./workspace"


def set_workspace_dir(path: str) -> None:
    """设置文件读写工具的工作区目录（在解析 CLI 参数后调用）。"""
    global _workspace_dir
    _workspace_dir = path


def get_workspace_base() -> str:
    """返回工作区目录的绝对路径，在工具 execute 时惰性调用。"""
    return os.path.abspath(_workspace_dir)
# --- 工作区配置结束 ---


class Tool(ABC):
    """所有工具继承此类,提供name，description 和 execute 方法"""
    name: str
    description: str

    @abstractmethod
    def execute(self, input: str) -> str:
        """执行工具逻辑，input 是模型传来的参数字符串"""
    