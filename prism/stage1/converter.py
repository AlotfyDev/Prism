"""Document converters: Markdown, HTML, PDF (deferred)."""

from pydantic import BaseModel, Field


class RawMarkdown(BaseModel):
    """Pydantic wrapper for raw Markdown text.

    Used as the output type for MarkdownLoader to satisfy the
    ProcessingUnit[InputT, OutputT, ConfigT] contract where OutputT
    must be bound to BaseModel.
    """
    content: str = Field(description="Raw Markdown text content")
    source_path: str = Field(description="Original file path")

    def __len__(self) -> int:
        return len(self.content)
