"""Stage 2: Markdown AST parser using markdown-it-py."""

from typing import Optional

from markdown_it import MarkdownIt
from markdown_it.token import Token

from prism.schemas.physical import MarkdownNode, NodeType, TopologyConfig
from prism.schemas.token import Stage1Output
from prism.stage2.pipeline_models import ParserOutput


# Map markdown-it-py token types to our NodeType
_TOKEN_TYPE_MAP: dict[str, NodeType] = {
    "heading_open": NodeType.HEADING,
    "paragraph_open": NodeType.PARAGRAPH,
    "table_open": NodeType.TABLE,
    "bullet_list_open": NodeType.LIST,
    "ordered_list_open": NodeType.LIST,
    "list_item_open": NodeType.LIST_ITEM,
    "fence": NodeType.CODE_BLOCK,
    "code_block": NodeType.CODE_BLOCK,
    "blockquote_open": NodeType.BLOCKQUOTE,
    "hr": NodeType.HR,
}

# Opening/closing token pairs for tree building
_OPEN_TOKENS = {
    "heading_open",
    "paragraph_open",
    "table_open",
    "tbody_open",
    "thead_open",
    "tr_open",
    "th_open",
    "td_open",
    "bullet_list_open",
    "ordered_list_open",
    "list_item_open",
    "blockquote_open",
}

_CLOSE_TOKENS = {
    "heading_close",
    "paragraph_close",
    "table_close",
    "tbody_close",
    "thead_close",
    "tr_close",
    "th_close",
    "td_close",
    "bullet_list_close",
    "ordered_list_close",
    "list_item_close",
    "blockquote_close",
}

_CLOSE_TOKENS = {
    "heading_close",
    "paragraph_close",
    "table_close",
    "tbody_close",
    "thead_close",
    "tr_close",
    "th_close",
    "td_close",
    "bullet_list_close",
    "ordered_list_close",
    "list_item_close",
    "blockquote_close",
}

# Container tokens that should not appear as leaf nodes
_CONTAINER_TYPES = _OPEN_TOKENS | _CLOSE_TOKENS


def _get_markdown_it() -> MarkdownIt:
    """Create a MarkdownIt instance with GFM tables enabled."""
    md = MarkdownIt("commonmark").enable("table")
    return md


def _token_to_node_type(token_type: str) -> Optional[NodeType]:
    """Map markdown-it-py token type to NodeType."""
    return _TOKEN_TYPE_MAP.get(token_type)


def _extract_raw_content(
    tokens: list[Token],
    source_text: str,
    start_idx: int,
    end_idx: int,
) -> str:
    """Extract raw markdown content from token span in source text."""
    start_token = tokens[start_idx]
    end_token = tokens[end_idx - 1] if end_idx > start_idx else start_token

    start_line = start_token.map[0] if start_token.map else 0
    end_line = end_token.map[1] if end_token.map else (start_line + 1)

    lines = source_text.split("\n")
    selected = lines[start_line:end_line]
    return "\n".join(selected)


def _build_tree(
    tokens: list[Token],
    source_text: str,
) -> list[MarkdownNode]:
    """Convert flat markdown-it-py token stream to tree of MarkdownNode."""
    root_nodes: list[MarkdownNode] = []
    stack: list[tuple[MarkdownNode, int]] = []  # (node, open_token_index)

    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Inline tokens carry the actual text content
        if token.type == "inline":
            if stack:
                parent, _ = stack[-1]
                content = token.content.strip()
                if content:
                    char_start, char_end = _compute_char_offsets(
                        tokens, i, source_text
                    )
                    inline_node = MarkdownNode(
                        node_type=NodeType.INLINE,
                        raw_content=content,
                        char_start=char_start,
                        char_end=char_end,
                    )
                    parent.children.append(inline_node)
            i += 1
            continue

        # Skip standalone close tokens (handled by stack logic)
        if token.type in _CLOSE_TOKENS:
            if stack:
                parent, open_idx = stack.pop()
                # Update char_end to close token's line if available
                if token.map:
                    lines = source_text.split("\n")
                    char_end = _line_to_char_offset(token.map[1], lines)
                    parent.char_end = char_end
            i += 1
            continue

        # Self-closing tokens (hr, fence, code_block)
        if token.type in ("hr", "fence", "code_block"):
            char_start, char_end = _compute_char_offsets(tokens, i, source_text)
            raw = _extract_raw_content(tokens, source_text, i, i + 1)
            attrs = {}
            if token.type == "fence":
                lang = token.info.strip() if token.info else ""
                if lang:
                    attrs["language"] = lang
                node_type = NodeType.CODE_BLOCK
            elif token.type == "code_block":
                # Indented code blocks have no markup and no language info
                is_indented = not getattr(token, "markup", "")
                node_type = NodeType.INDENTED_CODE_BLOCK if is_indented else NodeType.CODE_BLOCK
            elif token.type == "hr":
                node_type = NodeType.HR
                markup = getattr(token, "markup", "---")
                if markup:
                    attrs["markup"] = markup
            else:
                node_type = NodeType.CODE_BLOCK

            node = MarkdownNode(
                node_type=node_type,
                raw_content=raw,
                char_start=char_start,
                char_end=char_end,
                attributes=attrs,
            )
            if stack:
                stack[-1][0].children.append(node)
            else:
                root_nodes.append(node)
            i += 1
            continue

        # Opening tokens
        if token.type in _OPEN_TOKENS:
            node_type = _token_to_node_type(token.type)
            if node_type is None:
                # Skip unknown container types (tbody, thead, tr, etc.)
                i += 1
                continue

            char_start, _ = _compute_char_offsets(tokens, i, source_text)
            raw = _extract_raw_content(tokens, source_text, i, i + 1)

            # Determine level for headings
            level = None
            if node_type == NodeType.HEADING and token.tag:
                level = int(token.tag[1:])
            elif node_type == NodeType.LIST:
                level = token.level

            attrs = {}
            if node_type == NodeType.LIST:
                attrs["style"] = "unordered" if token.tag == "ul" else "ordered"
            elif node_type == NodeType.HEADING:
                markup = getattr(token, "markup", "#")
                if markup and markup in ("=", "-"):
                    attrs["heading_style"] = "setext"
                else:
                    attrs["heading_style"] = "atx"

            node = MarkdownNode(
                node_type=node_type,
                raw_content=raw,
                char_start=char_start,
                level=level,
                attributes=attrs,
            )

            if stack:
                stack[-1][0].children.append(node)
            else:
                root_nodes.append(node)

            stack.append((node, i))
            i += 1
            continue

        i += 1

    # Collapse paragraph-only children into parent where appropriate
    root_nodes = _collapse_inline_only(root_nodes)

    return root_nodes


def _compute_char_offsets(
    tokens: list[Token],
    index: int,
    source_text: str,
) -> tuple[Optional[int], Optional[int]]:
    """Compute char_start/char_end from token map."""
    token = tokens[index]
    if not token.map:
        return None, None

    lines = source_text.split("\n")
    char_start = _line_to_char_offset(token.map[0], lines)
    char_end = _line_to_char_offset(token.map[1], lines)
    return char_start, char_end


def _line_to_char_offset(line_number: int, lines: list[str]) -> int:
    """Convert line number to character offset in source text."""
    offset = 0
    for i in range(line_number):
        offset += len(lines[i]) + 1  # +1 for newline
    return offset


def _collapse_inline_only(nodes: list[MarkdownNode]) -> list[MarkdownNode]:
    """Collapse paragraphs that only contain inline children.

    If a PARAGRAPH node has only INLINE children, merge the inline
    content into the paragraph's raw_content for cleaner output.
    """
    result = []
    for node in nodes:
        if node.node_type == NodeType.PARAGRAPH and node.children:
            # Already has proper raw_content from extraction
            pass
        elif node.children:
            node.children = _collapse_inline_only(node.children)
        result.append(node)
    return result


class MarkdownItParser:
    """Parse Markdown into AST using markdown-it-py.

    Implements ProcessingUnit[Stage1Output, list[MarkdownNode], TopologyConfig].
    Parses raw Markdown text from Stage1Output.source_text into a tree
    of MarkdownNode objects with character offsets for token mapping.
    """

    @property
    def tier(self) -> str:
        return "python_nlp"

    @property
    def version(self) -> str:
        return "v1.0.0"

    def name(self) -> str:
        return "MarkdownItParser"

    def process(
        self,
        input_data: Stage1Output,
        config: Optional[TopologyConfig] = None,
    ) -> list[MarkdownNode]:
        """Parse Markdown text into AST tree.

        Args:
            input_data: Stage1Output containing source_text.
            config: Optional topology configuration (unused by parser,
                reserved for downstream classifier).

        Returns:
            List of root-level MarkdownNode objects.
        """
        source_text = input_data.source_text
        if not source_text.strip():
            return []

        md = _get_markdown_it()
        tokens = md.parse(source_text)
        return _build_tree(tokens, source_text)

    def validate_input(self, input_data: Stage1Output) -> tuple[bool, str]:
        """Verify input has non-empty source text."""
        if not input_data.source_text.strip():
            return False, "source_text is empty"
        return True, ""

    def validate_output(
        self,
        output_data: list[MarkdownNode],
    ) -> tuple[bool, str]:
        """Verify output is non-empty list of valid MarkdownNode objects."""
        if not output_data:
            return False, "No nodes parsed from input"
        for node in output_data:
            if not isinstance(node, MarkdownNode):
                return False, f"Invalid node type: {type(node)}"
            if not node.raw_content:
                return False, "Node has empty raw_content"
        return True, ""
