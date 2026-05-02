"""Stage 2.2b: LayerClassifier — orchestrates detectors to produce DetectedLayersReport.

Takes list[MarkdownNode] from MarkdownItParser, dispatches to all 10
detectors, and assembles a DetectedLayersReport.
"""

from typing import Optional

from prism.schemas.enums import LayerType
from prism.schemas.physical import (
    DetectedLayersReport,
    MarkdownNode,
    TopologyConfig,
)
from prism.stage2.layers.base import LayerRegistry
from prism.stage2.layers.specific_detectors import (
    BlockquoteDetector,
    CodeBlockDetector,
    DiagramDetector,
    FootnoteDetector,
    HeadingDetector,
    ListDetector,
    MetadataDetector,
    ParagraphDetector,
    TableDetector,
    FigureDetector,
)

# All 10 detectors, instantiated once
_ALL_DETECTORS = [
    HeadingDetector(),
    ParagraphDetector(),
    TableDetector(),
    ListDetector(),
    CodeBlockDetector(),
    BlockquoteDetector(),
    MetadataDetector(),
    FootnoteDetector(),
    DiagramDetector(),
    FigureDetector(),
]


class LayerClassifier:
    """Orchestrate layer detectors to produce DetectedLayersReport.

    Implements the classification phase of Stage 2: dispatch to detectors,
    collect results, filter by config, and assemble the report.

    Input:  list[MarkdownNode] + TopologyConfig
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

    def classify(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
        config: Optional[TopologyConfig] = None,
    ) -> DetectedLayersReport:
        """Run all detectors and assemble a DetectedLayersReport.

        Args:
            nodes: Root-level MarkdownNode objects from the parser.
            source_text: Original Markdown source text.
            config: Optional topology config (controls which types to detect).

        Returns:
            DetectedLayersReport with all detected instances.
        """
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

    def validate_input(
        self,
        nodes: list[MarkdownNode],
        source_text: str,
    ) -> tuple[bool, str]:
        """Verify input has non-empty nodes and source text."""
        if not nodes:
            return False, "No AST nodes to classify"
        if not source_text.strip():
            return False, "source_text is empty"
        return True, ""

    def validate_output(
        self,
        report: DetectedLayersReport,
    ) -> tuple[bool, str]:
        """Verify report has at least one detected instance."""
        if report.total_instances == 0:
            return False, "No layer instances detected"
        return True, ""
