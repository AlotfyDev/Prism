"""Indentation Analyzer — Heading indentation pattern analysis.

Analyzes heading indentation to detect outline formats vs standard markdown.
Reliability: 90% — 10% uncertainty from non-space indentation.
"""

from __future__ import annotations

from prism.schemas.physical import HeadingComponent
from prism.stage2.aggregation.aggregation_models import (
    HeadingAnomaly,
    IndentationPattern,
    IndentationPatternInfo,
)


class IndentationAnalyzer:
    """Analyzes heading indentation patterns for grouping."""

    # ------------------------------------------------------------------
    # IAggregator Protocol
    # ------------------------------------------------------------------

    def aggregate(self, input_data: list[HeadingComponent]) -> IndentationPattern:
        return self._analyze_indentation(input_data)

    def validate_input(self, input_data: list[HeadingComponent]) -> tuple[bool, str]:
        if not isinstance(input_data, list):
            return False, "Input must be a list of HeadingComponent"
        for h in input_data:
            if not isinstance(h, HeadingComponent):
                return False, "All items must be HeadingComponent"
        return True, ""

    def validate_output(self, output_data: IndentationPattern) -> tuple[bool, str]:
        if output_data.total_headings < 0:
            return False, "total_headings must be >= 0"
        return True, ""

    def name(self) -> str:
        return "IndentationAnalyzer"

    @property
    def tier(self) -> str:
        return "rules"

    @property
    def version(self) -> str:
        return "1.0.0"

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    def _analyze_indentation(self, headings: list[HeadingComponent]) -> IndentationPattern:
        """Analyze heading indentation patterns."""
        if not headings:
            return IndentationPattern(
                headings=[],
                is_consistent=True,
                levels=[],
                pattern_type="standard",
                groups_by_indent={},
                anomalies=[],
                total_headings=0,
            )

        # Extract indentation for each heading
        heading_infos = []
        indent_groups: dict[int, list[str]] = {}

        for h in sorted(headings, key=lambda x: x.char_start):
            indent = self._extract_indentation(h.raw_content)
            info = IndentationPatternInfo(
                heading_id=h.component_id,
                level=h.level,
                indentation=indent,
            )
            heading_infos.append(info)

            if indent not in indent_groups:
                indent_groups[indent] = []
            indent_groups[indent].append(h.component_id)

        # Get unique indentation levels
        levels = sorted(indent_groups.keys())

        # Determine pattern type
        pattern_type = self._classify_pattern(levels)
        is_consistent = pattern_type != "mixed"

        # Detect anomalies
        anomalies = self._find_anomalies(heading_infos, levels, pattern_type)

        return IndentationPattern(
            headings=heading_infos,
            is_consistent=is_consistent,
            levels=levels,
            pattern_type=pattern_type,
            groups_by_indent=indent_groups,
            anomalies=anomalies,
            total_headings=len(heading_infos),
        )

    def _extract_indentation(self, raw_content: str) -> int:
        """Extract leading whitespace count from heading raw content."""
        count = 0
        for ch in raw_content:
            if ch == " ":
                count += 1
            elif ch == "\t":
                count += 4  # Tab = 4 spaces
            else:
                break
        return count

    def _classify_pattern(self, levels: list[int]) -> str:
        """Classify indentation pattern type."""
        if not levels:
            return "standard"

        if len(levels) == 1 and levels[0] == 0:
            return "standard"

        # Check if levels follow consistent increment (0, 2, 4, 6...)
        if len(levels) > 1:
            diffs = [levels[i+1] - levels[i] for i in range(len(levels)-1)]
            if all(d == diffs[0] for d in diffs) and diffs[0] > 0:
                return "indented"

        # Mixed — inconsistent increments
        return "mixed"
    def _find_anomalies(
        self,
        heading_infos: list[IndentationPatternInfo],
        levels: list[int],
        pattern_type: str,
    ) -> list[HeadingAnomaly]:
        """Find headings that break the indentation pattern."""
        anomalies = []

        if pattern_type == "standard":
            # All should be at level 0
            for hi in heading_infos:
                if hi.indentation != 0:
                    anomalies.append(HeadingAnomaly(
                        heading_id=hi.heading_id,
                        expected_indent=0,
                        actual_indent=hi.indentation,
                        level=hi.level,
                    ))

        elif pattern_type == "indented":
            # Should follow consistent pattern
            if len(levels) > 1:
                step = levels[1] - levels[0]
                for hi in heading_infos:
                    expected = (hi.level - 1) * step
                    if hi.indentation != expected:
                        anomalies.append(HeadingAnomaly(
                            heading_id=hi.heading_id,
                            expected_indent=expected,
                            actual_indent=hi.indentation,
                            level=hi.level,
                        ))

        # Mixed pattern — flag outliers
        elif pattern_type == "mixed":
            # Find most common indentation
            from collections import Counter
            indent_counts = Counter(hi.indentation for hi in heading_infos)
            most_common_indent = indent_counts.most_common(1)[0][0]

            for hi in heading_infos:
                if hi.indentation != most_common_indent:
                    anomalies.append(HeadingAnomaly(
                        heading_id=hi.heading_id,
                        expected_indent=most_common_indent,
                        actual_indent=hi.indentation,
                        level=hi.level,
                    ))

        return anomalies
