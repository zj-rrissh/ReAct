
class LLMClient:
    def __init__(self,model_name: str, adapter):    # adapter 为实际调用函数
        self.model = model_name
        self.adapter = adapter
        
    def generate(self, prompt: str) -> str:
        """调用LLM,返回文本响应"""
        return self.adapter(self.model,prompt)