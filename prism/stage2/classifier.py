"""Stage 2.2b: LayerClassifier — orchestrates detectors to produce DetectedLayersReport.

Takes list[MarkdownNode] from MarkdownItParser, dispatches to all 15
detectors, and assembles a DetectedLayersReport.
"""

from typing import Optional, overload

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    DetectedLayersReport,
    MarkdownNode,
    TopologyConfig,
)
from prism.stage2.layers.detectors import LayerDetector
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
    UnifiedListDetector,
)
from prism.stage2.pipeline_models import ClassifierInput

# All 15 concrete detectors, instantiated once
_ALL_DETECTORS: list[LayerDetector] = [
    ASTHeadingDetector(),
    ASTParagraphDetector(),
    ASTTableDetector(),
    UnifiedListDetector(),
    UnifiedCodeBlockDetector(),
    ASTBlockquoteDetector(),
    HybridMetadataDetector(),
    UnifiedFootnoteDetector(),
    HeuristicDiagramDetector(),
    RegexFigureDetector(),
    RegexInlineCodeDetector(),
    RegexEmphasisDetector(),
    UnifiedLinkDetector(),
    UnifiedHTMLBlockDetector(),
    UnifiedHTMLInlineDetector(),
]


class LayerClassifier:
    """Orchestrate layer detectors to produce DetectedLayersReport.

    Implements the classification phase of Stage 2: dispatch to detectors,
    collect results, filter by config, and assemble the report.

    Input:  ClassifierInput (nodes + source_text)
    Output: DetectedLayersReport
    """

    @property
    def tier(self) -> str:
        return "orchestrator"

    @property
    def version(self) -> str:
        return "v1.0.0"

    def name(self) -> str:
        return "LayerClassifier"

    def process(
        self,
        input_data: ClassifierInput,
        config: Optional[TopologyConfig] = None,
    ) -> DetectedLayersReport:
        """Run all detectors and assemble a DetectedLayersReport.

        Args:
            input_data: ClassifierInput with nodes and source_text.
            config: Optional topology config (controls which types to detect).

        Returns:
            DetectedLayersReport with all detected instances.
        """
        nodes = input_data.nodes
        source_text = input_data.source_text

        allowed_types: set[LayerType] = set(LayerType)
        if config is not None and config.layer_types_to_detect:
            allowed_types = set(config.layer_types_to_detect)

        instances: dict[LayerType, list] = {}

        for detector in _ALL_DETECTORS:
            if detector.layer_type not in allowed_types:
                continue

            detected = detector.detect(nodes, source_text)
            if detected:
                instances[detector.layer_type] = detected

        return DetectedLayersReport(
            source_text=source_text,
            instances=instances,
        )

    # Backward compatibility: legacy classify() method
    @overload
    def classify(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
        config: Optional[TopologyConfig] = ...,
    ) -> DetectedLayersReport: ...

    def classify(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
        config: Optional[TopologyConfig] = None,
    ) -> DetectedLayersReport:
        """Legacy: calls process() with wrapped input."""
        return self.process(
            ClassifierInput(nodes=nodes, source_text=source_text),
            config=config,
        )

    # ------------------------------------------------------------------
    # Validation: primary signatures (type-safe)
    # ------------------------------------------------------------------

    def validate_input(
        self,
        input_data: ClassifierInput,
    ) -> tuple[bool, str]:
        """Verify input has non-empty nodes and source text."""
        if not input_data.nodes:
            return False, "No AST nodes to classify"
        if not input_data.source_text.strip():
            return False, "source_text is empty"
        return True, ""

    def validate_output(
        self,
        output_data: DetectedLayersReport,
    ) -> tuple[bool, str]:
        """Verify report has at least one detected instance."""
        if output_data.total_instances == 0:
            return False, "No layer instances detected"
        return True, ""
