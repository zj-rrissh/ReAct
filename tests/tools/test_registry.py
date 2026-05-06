"""Tool 注册表测试 (6 用例)。"""

from tools.base import Tool
from tools.registry import register_tool, get_all_tools, _tool_registry


class TestRegisterTool:
    def test_register_tool_with_custom_name(self):
        @register_tool(name="custom_name")
        class MyTool(Tool):
            name = "my_tool"
            description = "test"

            def execute(self, input: str) -> str:
                return input

        assert "custom_name" in _tool_registry
        assert _tool_registry["custom_name"] is MyTool

    def test_register_tool_with_default_name_from_class(self):
        @register_tool()
        class AnotherTool(Tool):
            name = "another"
            description = "test"

            def execute(self, input: str) -> str:
                return input

        assert "AnotherTool" in _tool_registry
        assert _tool_registry["AnotherTool"] is AnotherTool

    def test_get_all_tools_returns_copy_not_reference(self):
        @register_tool(name="copy_test")
        class CopyTool(Tool):
            name = "copy_test"
            description = "test"

            def execute(self, input: str) -> str:
                return input

        result = get_all_tools()
        result["new_key"] = CopyTool
        assert "new_key" not in _tool_registry

    def test_get_all_tools_returns_all_registered_tools(self):
        @register_tool(name="tool_a")
        class ToolA(Tool):
            name = "tool_a"
            description = "a"

            def execute(self, input: str) -> str:
                return input

        @register_tool(name="tool_b")
        class ToolB(Tool):
            name = "tool_b"
            description = "b"

            def execute(self, input: str) -> str:
                return input

        all_tools = get_all_tools()
        assert "tool_a" in all_tools
        assert "tool_b" in all_tools

    def test_register_same_name_overwrites_previous(self):
        @register_tool(name="same")
        class ToolV1(Tool):
            name = "v1"
            description = "v1"

            def execute(self, input: str) -> str:
                return "v1"

        @register_tool(name="same")
        class ToolV2(Tool):
            name = "v2"
            description = "v2"

            def execute(self, input: str) -> str:
                return "v2"

        assert _tool_registry["same"] is ToolV2

    def test_register_tool_decorator_returns_original_class(self):
        @register_tool(name="return_test")
        class ReturnTool(Tool):
            name = "return_test"
            description = "test"

            def execute(self, input: str) -> str:
                return input

        assert ReturnTool.name == "return_test"
