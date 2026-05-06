"""FileReadTool 测试 (9 用例)。"""

import pytest
from tools.file_reader import FileReadTool


@pytest.fixture
def reader():
    return FileReadTool()


class TestFileReadTool:
    def test_read_existing_file_returns_content(self, reader, sample_text_file):
        result = reader.execute(sample_text_file)
        assert "Hello ReAct Test" in result

    def test_read_nonexistent_file_returns_error(self, reader):
        result = reader.execute("nonexistent_file.txt")
        assert "错误" in result
        assert "不存在" in result

    def test_path_traversal_prevented_double_dot(self, reader):
        result = reader.execute("../etc/passwd")
        assert "错误" in result
        assert "不允许" in result

    def test_path_traversal_prevented_absolute_path(self, reader):
        result = reader.execute("/etc/passwd")
        assert "错误" in result
        assert "不允许" in result

    def test_path_traversal_prevented_outside_workspace(self, reader):
        result = reader.execute("../../../../etc/hostname")
        assert "错误" in result
        assert "不允许" in result

    def test_read_file_respects_workspace_dir_change(self, workspace_dir, reader):
        sub = workspace_dir / "sub"
        sub.mkdir()
        f = sub / "inner.txt"
        f.write_text("inner content", encoding="utf-8")
        result = reader.execute("sub/inner.txt")
        assert "inner content" in result

    def test_read_file_with_quoted_path(self, reader, sample_text_file):
        result = reader.execute(f"'{sample_text_file}'")
        assert "Hello ReAct Test" in result

    def test_read_file_input_with_extra_spaces(self, reader, sample_text_file):
        result = reader.execute(f"  {sample_text_file}  ")
        assert "Hello ReAct Test" in result

    def test_read_file_permission_error_handling(self, reader, workspace_dir):
        readonly = workspace_dir / "readonly.txt"
        readonly.write_text("secret", encoding="utf-8")
        readonly.chmod(0o000)
        try:
            result = reader.execute("readonly.txt")
            assert "错误" in result or "失败" in result
        finally:
            readonly.chmod(0o644)
