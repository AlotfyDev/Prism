"""Unit tests for MarkdownLoader (P1.1)."""

import pytest
from pathlib import Path

from prism.stage1.loader import MarkdownLoader
from prism.stage1.converter import RawMarkdown
from prism.schemas import Stage1Input, TokenizationConfig


class TestRawMarkdown:
    """Tests for the RawMarkdown wrapper model."""

    def test_create_valid(self):
        """RawMarkdown can be created with content and source."""
        rm = RawMarkdown(content="# Hello", source_path="/test.md")
        assert rm.content == "# Hello"
        assert rm.source_path == "/test.md"

    def test_len_returns_content_length(self):
        """len() returns the length of content."""
        rm = RawMarkdown(content="Hello", source_path="/test.md")
        assert len(rm) == 5

    def test_empty_content(self):
        """RawMarkdown accepts empty content."""
        rm = RawMarkdown(content="", source_path="/test.md")
        assert rm.content == ""
        assert len(rm) == 0


class TestMarkdownLoaderInstantiation:
    """Tests for MarkdownLoader construction."""

    def test_can_instantiate(self):
        """MarkdownLoader can be instantiated."""
        loader = MarkdownLoader()
        assert isinstance(loader.name(), str)

    def test_name_is_descriptive(self):
        """name() returns a descriptive string."""
        loader = MarkdownLoader()
        assert "markdown" in loader.name().lower()

    def test_tier_is_python_nlp(self):
        """tier returns python_nlp since it's a pure Python file reader."""
        loader = MarkdownLoader()
        assert loader.tier == "python_nlp"


class TestMarkdownLoaderValidateInput:
    """Tests for MarkdownLoader input validation."""

    def test_valid_file_path_input(self, tmp_path: Path):
        """validate_input returns True for existing readable file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Hello", encoding="utf-8")
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = loader.validate_input(input_data)
        assert is_valid is True
        assert error_msg == ""

    def test_missing_file_input(self, tmp_path: Path):
        """validate_input returns False for non-existent file."""
        missing_file = tmp_path / "nonexistent.md"
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(missing_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = loader.validate_input(input_data)
        assert is_valid is False
        assert "not exist" in error_msg.lower() or "missing" in error_msg.lower()

    def test_directory_instead_of_file(self, tmp_path: Path):
        """validate_input returns False when path is a directory."""
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(tmp_path),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        is_valid, error_msg = loader.validate_input(input_data)
        assert is_valid is False


class TestMarkdownLoaderProcess:
    """Tests for MarkdownLoader.process() — the core loading functionality."""

    def test_load_simple_markdown(self, tmp_path: Path):
        """Loads a simple markdown file and returns its content."""
        content = "# Title\n\nThis is a paragraph.\n"
        test_file = tmp_path / "simple.md"
        test_file.write_text(content, encoding="utf-8")
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        result = loader.process(input_data, TokenizationConfig())
        assert isinstance(result, RawMarkdown)
        assert result.content == content
        assert result.source_path == str(test_file)

    def test_load_markdown_with_code_blocks(self, tmp_path: Path):
        """Loads markdown containing code blocks."""
        content = """```python
def hello():
    print("world")
```

Some text.
"""
        test_file = tmp_path / "code.md"
        test_file.write_text(content, encoding="utf-8")
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        result = loader.process(input_data, TokenizationConfig())
        assert isinstance(result, RawMarkdown)
        assert result.content == content

    def test_load_markdown_with_tables(self, tmp_path: Path):
        """Loads markdown containing tables."""
        content = """| Name | Value |
|------|-------|
| A    | 1     |
| B    | 2     |
"""
        test_file = tmp_path / "table.md"
        test_file.write_text(content, encoding="utf-8")
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        result = loader.process(input_data, TokenizationConfig())
        assert isinstance(result, RawMarkdown)
        assert result.content == content

    def test_load_markdown_with_lists(self, tmp_path: Path):
        """Loads markdown containing lists."""
        content = """- Item 1
- Item 2
  - Nested 1
  - Nested 2
"""
        test_file = tmp_path / "list.md"
        test_file.write_text(content, encoding="utf-8")
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        result = loader.process(input_data, TokenizationConfig())
        assert isinstance(result, RawMarkdown)
        assert result.content == content

    def test_load_empty_file(self, tmp_path: Path):
        """Loads an empty markdown file."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("", encoding="utf-8")
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        result = loader.process(input_data, TokenizationConfig())
        assert isinstance(result, RawMarkdown)
        assert result.content == ""

    def test_load_unicode_content(self, tmp_path: Path):
        """Loads markdown with unicode characters."""
        content = "# مرحبا\n\n日本語テスト 🎉\n"
        test_file = tmp_path / "unicode.md"
        test_file.write_text(content, encoding="utf-8")
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(test_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        result = loader.process(input_data, TokenizationConfig())
        assert isinstance(result, RawMarkdown)
        assert result.content == content


class TestMarkdownLoaderErrors:
    """Tests for error handling in MarkdownLoader."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path):
        """process() raises FileNotFoundError for missing file."""
        missing_file = tmp_path / "nonexistent.md"
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(missing_file),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        with pytest.raises(FileNotFoundError):
            loader.process(input_data, TokenizationConfig())

    def test_directory_raises_is_a_directory(self, tmp_path: Path):
        """process() raises IsADirectoryError when path is a directory."""
        loader = MarkdownLoader()
        input_data = Stage1Input(
            source=str(tmp_path),
            source_type="markdown",
            config=TokenizationConfig(),
        )
        with pytest.raises(IsADirectoryError):
            loader.process(input_data, TokenizationConfig())


class TestMarkdownLoaderValidateOutput:
    """Tests for MarkdownLoader output validation."""

    def test_valid_output_passes(self):
        """validate_output returns True for valid RawMarkdown."""
        loader = MarkdownLoader()
        output = RawMarkdown(content="# Hello\n", source_path="/test.md")
        is_valid, error_msg = loader.validate_output(output)
        assert is_valid is True
        assert error_msg == ""

    def test_empty_content_passes(self):
        """validate_output returns True for empty content."""
        loader = MarkdownLoader()
        output = RawMarkdown(content="", source_path="/test.md")
        is_valid, error_msg = loader.validate_output(output)
        assert is_valid is True

    def test_none_fails(self):
        """validate_output returns False for None."""
        loader = MarkdownLoader()
        is_valid, error_msg = loader.validate_output(None)
        assert is_valid is False


class TestMarkdownLoaderWithSampleFixture:
    """Tests using the actual sample fixture file."""

    def test_load_sample_markdown(self, fixtures_dir: Path):
        """Loads the sample markdown fixture successfully."""
        sample_file = fixtures_dir / "sample_simple.md"
        if sample_file.exists():
            loader = MarkdownLoader()
            expected = sample_file.read_text(encoding="utf-8")
            input_data = Stage1Input(
                source=str(sample_file),
                source_type="markdown",
                config=TokenizationConfig(),
            )
            result = loader.process(input_data, TokenizationConfig())
            assert isinstance(result, RawMarkdown)
            assert result.content == expected
            assert result.source_path == str(sample_file)
