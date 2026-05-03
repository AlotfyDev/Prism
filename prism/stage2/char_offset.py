"""Char offset utilities for converting line numbers ↔ character offsets.

mrkdwn_analysis returns 1-indexed line numbers. Prism requires
char_start/char_end (0-indexed character offsets into source text).

These utilities bridge that gap.
"""


def line_to_char_offset(line_number: int, source_text: str) -> int:
    """Convert a 1-indexed line number to a 0-indexed char offset.

    Args:
        line_number: 1-indexed line number (1 = first line).
        source_text: Full Markdown source text.

    Returns:
        0-indexed character offset to the start of the given line.
    """
    if line_number < 1:
        return 0
    lines = source_text.split("\n")
    if line_number > len(lines):
        return len(source_text)
    offset = 0
    for i in range(line_number - 1):
        offset += len(lines[i]) + 1
    return offset


def compute_char_range_for_line(
    line_number: int,
    source_text: str,
    line_content: str = "",
) -> tuple[int, int]:
    """Compute (char_start, char_end) for a given line number.

    If line_content is provided, char_end = char_start + len(line_content).
    Otherwise, char_end = start of next line (or end of text).

    Args:
        line_number: 1-indexed line number.
        source_text: Full Markdown source text.
        line_content: Optional content string on that line.

    Returns:
        Tuple of (char_start, char_end).
    """
    start = line_to_char_offset(line_number, source_text)
    if line_content:
        return start, start + len(line_content)
    lines = source_text.split("\n")
    if line_number <= len(lines):
        return start, start + len(lines[line_number - 1])
    return start, len(source_text)


def compute_char_range_for_line_segment(
    line_number: int,
    col_start: int,
    col_end: int,
    source_text: str,
) -> tuple[int, int]:
    """Compute (char_start, char_end) for a segment within a line.

    Args:
        line_number: 1-indexed line number.
        col_start: 0-indexed column start within the line.
        col_end: 0-indexed column end within the line (exclusive).
        source_text: Full Markdown source text.

    Returns:
        Tuple of (char_start, char_end).
    """
    base = line_to_char_offset(line_number, source_text)
    return base + col_start, base + col_end


def line_col_to_char_offset(
    line_number: int,
    col: int,
    source_text: str,
) -> int:
    """Convert (line, col) to absolute char offset.

    Args:
        line_number: 1-indexed line number.
        col: 0-indexed column within the line.
        source_text: Full Markdown source text.

    Returns:
        0-indexed character offset.
    """
    return line_to_char_offset(line_number, source_text) + col


def char_offset_to_line(char_offset: int, source_text: str) -> int:
    """Convert 0-indexed char offset to 0-indexed line number.

    Args:
        char_offset: Character offset into source_text.
        source_text: Full Markdown source text.

    Returns:
        0-indexed line number.
    """
    if char_offset <= 0:
        return 0
    return source_text[:char_offset].count("\n")
