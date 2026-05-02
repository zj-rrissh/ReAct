from abc import abstractmethod,ABC
from os import name


class Tool(ABC):
    """所有工具继承此类,提供name，description 和 execute 方法"""
    name: str
    description: str
    
    @abstractmethod
    def execute(self,input: str ) -> str:
        """执行工具逻辑，input 是模型传来的参数字符串"""
    