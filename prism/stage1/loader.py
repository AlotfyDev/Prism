"""Markdown file loader — reads .md files and returns raw text."""

from pathlib import Path

from pydantic import BaseModel

from prism.core.processing_unit import ProcessingUnit
from prism.schemas import Stage1Input, TokenizationConfig
from prism.stage1.converter import RawMarkdown


class MarkdownLoader(ProcessingUnit[Stage1Input, RawMarkdown, TokenizationConfig]):
    """Loads a Markdown file from disk and returns its raw content.

    Implements the ProcessingUnit contract to enable pipeline integration.
    Output is a RawMarkdown wrapper (Pydantic model containing the raw text),
    which satisfies the BaseModel constraint of ProcessingUnit.

    Docling/PDF support is deferred to Phase 2.
    """

    def process(self, input_data: Stage1Input, config: TokenizationConfig) -> RawMarkdown:
        source_path = Path(input_data.source)

        if not source_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {source_path}")

        if source_path.is_dir():
            raise IsADirectoryError(f"Path is a directory, not a file: {source_path}")

        content = source_path.read_text(encoding="utf-8-sig")
        return RawMarkdown(content=content, source_path=str(source_path))

    def validate_input(self, input_data: Stage1Input) -> tuple[bool, str]:
        source_path = Path(input_data.source)

        if not source_path.exists():
            return False, f"File does not exist: {source_path}"

        if source_path.is_dir():
            return False, f"Path is a directory, not a file: {source_path}"

        return True, ""

    def validate_output(self, output_data: RawMarkdown) -> tuple[bool, str]:
        if output_data is None:
            return False, "Output is None"

        if not isinstance(output_data, BaseModel):
            return False, f"Expected RawMarkdown, got {type(output_data)}"

        return True, ""

    def name(self) -> str:
        return "MarkdownLoader"

    @property
    def tier(self) -> str:
        return "python_nlp"
