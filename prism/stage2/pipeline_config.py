"""Stage 2 pipeline configuration — swappable unit registry.

Defines Stage2PipelineConfig which specifies which implementation
class to use for each Stage 2 processing step.

Usage:
    # Default pipeline (all current implementations)
    config = Stage2PipelineConfig()

    # Swap TokenSpanMapper for ML-based implementation
    config = Stage2PipelineConfig(
        token_span_mapper=MLTokenSpanMapper
    )

    # Swap multiple units
    config = Stage2PipelineConfig(
        parser=MistuneParser,
        component_mapper=MLComponentMapper,
    )
"""

from typing import Any

from pydantic import BaseModel, Field

from prism.stage2.aggregation.nlp.detector_correlation import DetectorCorrelation
from prism.stage2.aggregation.nlp.heading_sequence import HeadingSequenceAnalyzer
from prism.stage2.aggregation.rules.codeblock_aggregator import CodeBlockAggregator
from prism.stage2.aggregation.rules.indentation_analyzer import IndentationAnalyzer
from prism.stage2.aggregation.rules.list_aggregator import ListAggregator
from prism.stage2.aggregation.rules.nesting_validator import NestingValidator
from prism.stage2.aggregation.rules.table_aggregator import TableAggregator
from prism.stage2.aggregation.rules.token_range_aggregator import TokenRangeAggregator
from prism.stage2.aggregation.rules.topology_assembler import TopologyAssembler
from prism.stage2.classifier import LayerClassifier
from prism.stage2.hierarchy import HierarchyBuilder
from prism.stage2.mapper import ComponentMapper
from prism.stage2.parser import MarkdownItParser
from prism.stage2.token_span import TokenSpanMapper
from prism.stage2.topology import TopologyBuilder


class Stage2PipelineConfig(BaseModel):
    """Configuration for Stage2Pipeline — defines which implementation
    to use for each processing step. All defaults are the current implementations.

    To swap any unit, replace the class reference:
        config = Stage2PipelineConfig(token_span_mapper=MLTokenSpanMapper)
    """

    model_config = {"arbitrary_types_allowed": True}

    parser: type = Field(
        default=MarkdownItParser,
        description="IParser implementation class",
    )
    classifier: type = Field(
        default=LayerClassifier,
        description="IClassifier implementation class",
    )
    hierarchy_builder: type = Field(
        default=HierarchyBuilder,
        description="IHierarchyBuilder implementation class",
    )
    component_mapper: type = Field(
        default=ComponentMapper,
        description="IComponentMapper implementation class",
    )
    token_span_mapper: type = Field(
        default=TokenSpanMapper,
        description="ITokenSpanMapper implementation class",
    )
    topology_builder: type = Field(
        default=TopologyBuilder,
        description="ITopologyBuilder implementation class",
    )

    # Aggregation units (Phase 4b)
    token_range_aggregator: type = Field(
        default=TokenRangeAggregator,
        description="ITokenRangeAggregator implementation class",
    )
    table_aggregator: type = Field(
        default=TableAggregator,
        description="ITableAggregator implementation class",
    )
    list_aggregator: type = Field(
        default=ListAggregator,
        description="IListAggregator implementation class",
    )
    codeblock_aggregator: type = Field(
        default=CodeBlockAggregator,
        description="ICodeBlockAggregator implementation class",
    )
    heading_sequence_analyzer: type = Field(
        default=HeadingSequenceAnalyzer,
        description="IHeadingSequenceAnalyzer implementation class",
    )
    indentation_analyzer: type = Field(
        default=IndentationAnalyzer,
        description="IIndentationAnalyzer implementation class",
    )
    nesting_validator: type = Field(
        default=NestingValidator,
        description="INestingValidator implementation class",
    )
    topology_assembler: type = Field(
        default=TopologyAssembler,
        description="ITopologyAssembler implementation class",
    )
    detector_correlator: type = Field(
        default=DetectorCorrelation,
        description="IDetectorCorrelation implementation class",
    )

    def get_unit_classes(self) -> dict[str, type]:
        """Return dict of step_name -> implementation class."""
        return {
            "parser": self.parser,
            "classifier": self.classifier,
            "hierarchy_builder": self.hierarchy_builder,
            "component_mapper": self.component_mapper,
            "token_span_mapper": self.token_span_mapper,
            "topology_builder": self.topology_builder,
            "token_range_aggregator": self.token_range_aggregator,
            "table_aggregator": self.table_aggregator,
            "list_aggregator": self.list_aggregator,
            "codeblock_aggregator": self.codeblock_aggregator,
            "heading_sequence_analyzer": self.heading_sequence_analyzer,
            "indentation_analyzer": self.indentation_analyzer,
            "nesting_validator": self.nesting_validator,
            "topology_assembler": self.topology_assembler,
            "detector_correlator": self.detector_correlator,
        }
