"""Tool ABC + workspace 配置测试 (7 用例)。"""

import os
import tempfile

import pytest
from tools.base import Tool, set_workspace_dir, get_workspace_base


class TestWorkspaceConfig:
    def test_get_workspace_base_returns_absolute_path(self):
        abspath = get_workspace_base()
        assert os.path.isabs(abspath)

    def test_get_workspace_base_default_is_workspace(self):
        base = get_workspace_base()
        assert base.endswith("workspace")

    def test_set_workspace_dir_changes_base(self):
        original = get_workspace_base()
        try:
            set_workspace_dir("/tmp/test-workspace")
            new_base = get_workspace_base()
            assert new_base == "/tmp/test-workspace"
        finally:
            set_workspace_dir(original)

    def test_set_workspace_dir_absolute_path(self):
        original = get_workspace_base()
        try:
            with tempfile.TemporaryDirectory() as d:
                set_workspace_dir(d)
                assert get_workspace_base() == os.path.abspath(d)
        finally:
            set_workspace_dir(original)


class TestToolABC:
    def test_tool_is_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            Tool()

    def test_concrete_subclass_can_instantiate(self):
        class MyTool(Tool):
            name = "my_tool"
            description = "test"

            def execute(self, input: str) -> str:
                return input

        tool = MyTool()
        assert tool.name == "my_tool"

    def test_concrete_subclass_must_implement_execute(self):
        with pytest.raises(TypeError):

            class BadTool(Tool):
                name = "bad"
                description = "bad"

            BadTool()
