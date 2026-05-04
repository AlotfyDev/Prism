"""Stage 2 — Layer types hub.

Central import point for all layer-specific CRUD operations and detectors.

CRUD usage:
    from prism.stage2.layers import get_crud
    table_crud = get_crud(LayerType.TABLE)
    t = table_crud.create("tbl1", "| A | B |\\n| 1 | 2 |")

Detector contracts and concrete implementations:
    from prism.stage2.layers import HeadingDetector  # contract (ABC)
    from prism.stage2.layers import ASTHeadingDetector  # concrete
"""

from prism.schemas.enums import LayerType

from prism.stage2.layers.base import LayerCRUD, LayerRegistry
from prism.stage2.layers.detectors import (
    LayerDetector,
    HeadingDetector,
    ParagraphDetector,
    TableDetector,
    ListDetector,
    CodeBlockDetector,
    BlockquoteDetector,
    MetadataDetector,
    FootnoteDetector,
    FootnoteRefDetector,
    DiagramDetector,
    FigureDetector,
    InlineCodeDetector,
    EmphasisDetector,
    LinkDetector,
    HTMLBlockDetector,
    HTMLInlineDetector,
    HRDetector,
    IndentedCodeBlockDetector,
    _walk_ast,
    _build_instance,
    _scan_inline_nodes,
)
from prism.stage2.layers.specific_detectors import (
    ASTHeadingDetector,
    ASTParagraphDetector,
    ASTTableDetector,
    ASTBlockquoteDetector,
    HybridMetadataDetector,
    UnifiedFootnoteDetector,
    HeuristicDiagramDetector,
    RegexFigureDetector,
    RegexInlineCodeDetector,
    RegexEmphasisDetector,
    UnifiedLinkDetector,
    UnifiedHTMLBlockDetector,
    UnifiedHTMLInlineDetector,
    UnifiedCodeBlockDetector,
    HybridListDetector,
    ASTHRDetector,
    ASTIndentedCodeBlockDetector,
    RegexFootnoteRefDetector,
)
from prism.stage2.layers.task_list import TaskListCRUD
from prism.stage2.layers.horizontal_rule import HRCRUD
from prism.stage2.layers.indented_code_block import IndentedCodeBlockCRUD
# Import all layer CRUD modules to trigger auto-registration
from prism.stage2.layers.table import TableCRUD
from prism.stage2.layers.list import ListCRUD
from prism.stage2.layers.simple_layers import (
    HeadingCRUD,
    ParagraphCRUD,
    CodeBlockCRUD,
    BlockquoteCRUD,
    FootnoteCRUD,
    FootnoteRefCRUD,
    MetadataCRUD,
    FigureCRUD,
    DiagramCRUD,
    InlineCodeCRUD,
    EmphasisCRUD,
    LinkCRUD,
    HTMLBlockCRUD,
    HTMLInlineCRUD,
)


def get_crud(layer_type: LayerType) -> LayerCRUD:
    """Get the CRUD implementation for a layer type.

    Convenience wrapper around LayerRegistry.get().
    """
    return LayerRegistry.get(layer_type)


__all__ = [
    # Hub
    "LayerCRUD",
    "LayerRegistry",
    "get_crud",
    "LayerDetector",
    # Contracts (ABCs, one per LayerType)
    "HeadingDetector",
    "ParagraphDetector",
    "TableDetector",
    "ListDetector",
    "CodeBlockDetector",
    "BlockquoteDetector",
    "MetadataDetector",
    "FootnoteDetector",
    "FootnoteRefDetector",
    "DiagramDetector",
    "FigureDetector",
    "InlineCodeDetector",
    "EmphasisDetector",
    "LinkDetector",
    "HTMLBlockDetector",
    "HTMLInlineDetector",
    "HRDetector",
    "IndentedCodeBlockDetector",
    # Concrete implementations (AST-based)
    "ASTHeadingDetector",
    "ASTParagraphDetector",
    "ASTTableDetector",
    "ASTBlockquoteDetector",
    "ASTHRDetector",
    "ASTIndentedCodeBlockDetector",
    # Concrete implementations (Hybrid AST + raw text)
    "HybridMetadataDetector",
    # Concrete implementations (Compositional: Prism + mrkdwn_analysis)
    "UnifiedFootnoteDetector",
    "UnifiedCodeBlockDetector",
    "HybridListDetector",
    "UnifiedLinkDetector",
    "UnifiedHTMLBlockDetector",
    "UnifiedHTMLInlineDetector",
    # Concrete implementations (Heuristic)
    "HeuristicDiagramDetector",
    # Concrete implementations (Regex inline scanning)
    "RegexFigureDetector",
    "RegexInlineCodeDetector",
    "RegexEmphasisDetector",
    "RegexFootnoteRefDetector",
    # Utility functions
    "_walk_ast",
    "_build_instance",
    "_scan_inline_nodes",
    # CRUDs
    "TableCRUD",
    "ListCRUD",
    "HeadingCRUD",
    "ParagraphCRUD",
    "CodeBlockCRUD",
    "BlockquoteCRUD",
    "FootnoteCRUD",
    "FootnoteRefCRUD",
    "MetadataCRUD",
    "FigureCRUD",
    "DiagramCRUD",
    "InlineCodeCRUD",
    "EmphasisCRUD",
    "LinkCRUD",
    "HTMLBlockCRUD",
    "HTMLInlineCRUD",
    "TaskListCRUD",
    "HRCRUD",
    "IndentedCodeBlockCRUD",
]
