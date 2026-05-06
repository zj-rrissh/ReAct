"""FileWriteTool 测试 (11 用例)。"""

import pytest
from tools.file_writer import FileWriteTool


@pytest.fixture
def writer():
    return FileWriteTool()


class TestFileWriteTool:
    def test_write_file_success(self, writer, workspace_dir):
        result = writer.execute("test_output.txt Hello World")
        assert "成功" in result
        assert (workspace_dir / "test_output.txt").read_text(encoding="utf-8") == "Hello World"

    def test_write_file_content_is_correct(self, writer, workspace_dir):
        writer.execute("data.txt 多行内容\n第二行")
        content = (workspace_dir / "data.txt").read_text(encoding="utf-8")
        assert "多行内容" in content

    def test_overwrite_existing_file(self, writer, workspace_dir):
        f = workspace_dir / "overwrite.txt"
        f.write_text("old content", encoding="utf-8")
        writer.execute("overwrite.txt new content")
        assert f.read_text(encoding="utf-8") == "new content"

    def test_missing_space_separator_returns_error(self, writer):
        result = writer.execute("filename_only")
        assert "错误" in result

    def test_auto_create_parent_directory(self, writer, workspace_dir):
        writer.execute("subdir/nested/deep.txt hello")
        assert (workspace_dir / "subdir" / "nested" / "deep.txt").exists()

    def test_path_traversal_prevented(self, writer):
        result = writer.execute("../etc/passwd hacked")
        assert "错误" in result
        assert "不允许" in result

    def test_absolute_path_prevented(self, writer):
        result = writer.execute("/etc/cron.d/evil hacked")
        assert "错误" in result
        assert "不允许" in result

    def test_input_with_extra_leading_trailing_quotes(self, writer, workspace_dir):
        writer.execute("'quoted.txt quoted content'")
        f = workspace_dir / "quoted.txt"
        if f.exists():
            content = f.read_text(encoding="utf-8")
            assert "quoted" in content.lower()

    def test_write_file_respects_workspace_dir_change(self, writer, workspace_dir):
        assert (workspace_dir / "output.txt").exists() is False
        writer.execute("output.txt respect workspace")
        assert (workspace_dir / "output.txt").exists()

    def test_write_empty_content(self, writer, workspace_dir):
        result = writer.execute("empty.txt ")
        assert "错误" in result

    def test_write_content_with_spaces(self, writer, workspace_dir):
        writer.execute("multi.txt content with many spaces here")
        content = (workspace_dir / "multi.txt").read_text(encoding="utf-8")
        assert "content with many spaces here" == content
