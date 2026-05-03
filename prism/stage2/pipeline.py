"""Stage 2 pipeline — synchronous orchestrator.

Stage2Pipeline manages the complete Stage 2 workflow:
  Stage1Output → Parser → Classifier → DetectorCorrelator
    → HierarchyBuilder → ComponentMapper → TokenSpanMapper
    → TokenRangeAggregator → TableAggregator → ListAggregator
    → CodeBlockAggregator → HeadingSequenceAnalyzer
    → IndentationAnalyzer → NestingValidator → TopologyBuilder
    → TopologyAssembler → Stage2Output

Features:
- Each step is swappable via Stage2PipelineConfig
- Validation gates between each step
- PipelineStepError on validation failure
- Aggregation steps (Phase 4) enrich output with structural analysis
- Works as a single ProcessingUnit (callable from LangGraph)
"""

from typing import Any, Optional

from prism.schemas.physical import Stage2Output, TopologyConfig
from prism.schemas.token import Stage1Output
from prism.stage2.aggregation.aggregation_models import AssemblyInput
from prism.stage2.pipeline_config import Stage2PipelineConfig
from prism.stage2.pipeline_models import (
    ClassifierInput,
    HierarchyInput,
    MapperInput,
    TokenSpanInput,
    TopologyInput,
)


class PipelineStepError(Exception):
    """Raised when a pipeline step fails validation."""

    def __init__(
        self,
        step_name: str,
        validation_type: str,
        message: str,
    ) -> None:
        self.step_name = step_name
        self.validation_type = validation_type
        self.message = message
        super().__init__(
            f"Step '{step_name}' {validation_type} validation failed: {message}"
        )


class Stage2Pipeline:
    """Orchestrates Stage 2 as a single pipeline.

    Each step is swappable via Stage2PipelineConfig.
    Validation gates run between each step.
    On validation failure, raises PipelineStepError with details.

    Usage:
        pipeline = Stage2Pipeline()  # default config
        # OR
        pipeline = Stage2Pipeline(config=custom_config)

        output = pipeline.process(stage1_output, topology_config)
    """

    def __init__(
        self,
        config: Optional[Stage2PipelineConfig] = None,
    ) -> None:
        self.config = config or Stage2PipelineConfig()
        self._units: dict[str, Any] = self._instantiate_units()

    def _instantiate_units(self) -> dict[str, Any]:
        """Instantiate all processing units from config."""
        classes = self.config.get_unit_classes()
        return {name: cls() for name, cls in classes.items()}

    def process(
        self,
        input_data: Stage1Output,
        config: Optional[TopologyConfig] = None,
    ) -> Stage2Output:
        """Execute the full Stage 2 pipeline.

        Args:
            input_data: Stage1Output with source_text and tokens.
            config: Optional TopologyConfig for downstream units.

        Returns:
            Stage2Output with discovered layers and token mappings.

        Raises:
            PipelineStepError: If any step's input or output validation fails.
        """
        # Step 1: Parse Markdown → AST nodes
        nodes = self._units["parser"].process(input_data, config)
        self._validate_step("parser", input_data, nodes)

        # Step 2: Classify AST → DetectedLayersReport
        classifier_input = ClassifierInput(
            nodes=nodes,
            source_text=input_data.source_text,
        )
        report = self._units["classifier"].process(classifier_input, config)
        self._validate_step("classifier", classifier_input, report)

        # Step 3: Cross-detector correlation (Aggregation A2)
        correlated = self._units["detector_correlator"].aggregate(report)
        self._validate_step("detector_correlator", report, correlated)

        # Step 4: Build hierarchy → HierarchyTree
        hierarchy_input = HierarchyInput(report=report)
        tree = self._units["hierarchy_builder"].process(hierarchy_input, config)
        self._validate_step("hierarchy_builder", hierarchy_input, tree)

        # Step 5: Map components → MapperOutput
        mapper_input = MapperInput(tree=tree)
        mapper_output = self._units["component_mapper"].process(
            mapper_input, config
        )
        self._validate_step("component_mapper", mapper_input, mapper_output)

        # Step 6: Map tokens → TokenSpanOutput
        token_span_input = TokenSpanInput(
            components=mapper_output.components,
            stage1_output=input_data,
        )
        token_span_output = self._units["token_span_mapper"].process(
            token_span_input, config
        )
        self._validate_step(
            "token_span_mapper", token_span_input, token_span_output
        )

        # Aggregation Steps (Phase 4a/4b)

        # Step 7: Token Range Aggregator (B4)
        token_range_input = {
            "components": mapper_output.components,
            "stage1_output": input_data,
        }
        token_range_index = self._units["token_range_aggregator"].aggregate(
            token_range_input
        )
        self._validate_step("token_range_aggregator", token_range_input, token_range_index)

        # Step 8: Table Aggregator (B1)
        table_indices = self._units["table_aggregator"].aggregate(nodes)
        self._validate_step("table_aggregator", nodes, table_indices)

        # Step 9: List Aggregator (B2)
        list_indices = self._units["list_aggregator"].aggregate(nodes)
        self._validate_step("list_aggregator", nodes, list_indices)

        # Step 10: CodeBlock Aggregator (B3)
        codeblock_indices = self._units["codeblock_aggregator"].aggregate(nodes)
        self._validate_step("codeblock_aggregator", nodes, codeblock_indices)

        # Step 11: Heading Sequence Analyzer (A1)
        heading_components = [
            c for c in mapper_output.components
            if c.layer_type.value == "heading"
        ]
        heading_sequence = self._units["heading_sequence_analyzer"].aggregate(
            heading_components
        )
        self._validate_step("heading_sequence_analyzer", heading_components, heading_sequence)

        # Step 12: Indentation Analyzer (B5)
        indentation = self._units["indentation_analyzer"].aggregate(
            heading_components
        )
        self._validate_step("indentation_analyzer", heading_components, indentation)

        # Step 13: Nesting Validator (B6)
        component_dict = {c.component_id: c for c in mapper_output.components}
        nesting_validation = self._units["nesting_validator"].aggregate(
            component_dict
        )
        self._validate_step("nesting_validator", component_dict, nesting_validation)

        # Step 14: Build topology → Stage2Output (original)
        topology_input = TopologyInput(
            components=mapper_output.components,
            token_mapping=token_span_output.component_to_tokens,
        )
        output = self._units["topology_builder"].process(
            topology_input, config
        )
        self._validate_step("topology_builder", topology_input, output)

        # Step 15: Topology Assembler (B7) — enriches with aggregation results
        assembly_input = AssemblyInput(
            components=component_dict,
            heading_sequence=heading_sequence,
            correlations=correlated,
            token_range_index=token_range_index,
            nesting_validation=nesting_validation,
            indentation_pattern=indentation,
        )
        final_output = self._units["topology_assembler"].aggregate(assembly_input)
        self._validate_step("topology_assembler", assembly_input, final_output)

        return final_output

    def _validate_step(
        self,
        step_name: str,
        input_data: Any,
        output_data: Any,
    ) -> None:
        """Run input and output validation for a pipeline step.

        Raises:
            PipelineStepError: If validation fails.
        """
        unit = self._units[step_name]

        valid, msg = unit.validate_input(input_data)
        if not valid:
            raise PipelineStepError(step_name, "input", msg)

        valid, msg = unit.validate_output(output_data)
        if not valid:
            raise PipelineStepError(step_name, "output", msg)
