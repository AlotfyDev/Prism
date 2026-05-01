"""ValidationV1 — Token Integrity Gate for Stage 1.

Implements the ValidationUnit contract to verify that Stage1Output
meets all token integrity requirements before proceeding to Stage 2.

Checks:
  V1.1 — Sequential IDs (no gaps: T0, T1, ... TN)
  V1.2 — No empty tokens (token.text must have non-whitespace content)
  V1.3 — Metadata completeness (every token has metadata entry and vice versa)
  V1.4 — No overlapping character ranges
  V1.5 — Full coverage warning (all source chars accounted for)

Severity:
  CRITICAL — V1.1, V1.2, V1.3, V1.4 (pipeline must halt on failure)
  WARNING  — V1.5 (gaps from filtered whitespace are expected; non-whitespace gaps are critical)
"""

from prism.core.validation_unit import (
    ValidationCheck,
    ValidationReport,
    ValidationSeverity,
    ValidationUnit,
)
from prism.schemas import Stage1Output


class ValidationV1(ValidationUnit):
    """Token integrity validation gate for Stage 1 output."""

    def validate(self, data: Stage1Output) -> ValidationReport:
        if not isinstance(data, Stage1Output):
            return ValidationReport(
                stage="stage1",
                passed=False,
                checks=[
                    ValidationCheck(
                        id="V1.0",
                        name="V1.0_input_type",
                        passed=False,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Expected Stage1Output, got {type(data).__name__}",
                    )
                ],
            )

        checks: list[ValidationCheck] = []

        # V1.1: Sequential IDs
        checks.append(self._check_sequential_ids(data))

        # V1.2: No empty tokens
        checks.append(self._check_no_empty_tokens(data))

        # V1.3: Metadata completeness
        checks.append(self._check_metadata_completeness(data))

        # V1.4: No overlapping ranges
        checks.append(self._check_no_overlapping_ranges(data))

        # V1.5: Full coverage
        checks.append(self._check_full_coverage(data))

        passed = all(c.passed for c in checks)
        return ValidationReport(stage="stage1", passed=passed, checks=checks)

    def _check_sequential_ids(self, data: Stage1Output) -> ValidationCheck:
        """V1.1: Token IDs must be sequential T0, T1, ... TN with no gaps or duplicates."""
        if not data.tokens:
            return ValidationCheck(
                id="V1.1",
                name="V1.1_sequential_ids",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
                message="No tokens to validate (empty output)",
            )

        sorted_ids = sorted(data.tokens.keys(), key=lambda x: int(x[1:]))
        expected_ids = [f"T{i}" for i in range(len(sorted_ids))]

        if sorted_ids != expected_ids:
            missing = set(expected_ids) - set(sorted_ids)
            duplicates = len(sorted_ids) - len(set(sorted_ids))
            details = {}
            if missing:
                details["missing_ids"] = sorted(missing)
            if duplicates > 0:
                details["duplicate_count"] = duplicates

            message_parts = []
            if missing:
                message_parts.append(f"Missing IDs: {sorted(missing)}")
            if duplicates > 0:
                message_parts.append(f"{duplicates} duplicate ID(s)")
            if sorted_ids != sorted(set(sorted_ids)):
                message_parts.append("IDs out of order")

            return ValidationCheck(
                id="V1.1",
                name="V1.1_sequential_ids",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="; ".join(message_parts),
                details=details,
            )

        return ValidationCheck(
            id="V1.1",
            name="V1.1_sequential_ids",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message=f"{len(sorted_ids)} sequential IDs verified (T0..T{len(sorted_ids)-1})",
        )

    def _check_no_empty_tokens(self, data: Stage1Output) -> ValidationCheck:
        """V1.2: No token may have empty text (whitespace-only is fine if include_whitespace=True)."""
        include_ws = data.config.include_whitespace if data.config else True
        empty_tokens = []
        for token_id, token in data.tokens.items():
            if not token.text:
                empty_tokens.append(token_id)
            elif not include_ws and not token.text.strip():
                # Whitespace-only tokens when include_whitespace=False
                empty_tokens.append(token_id)

        if empty_tokens:
            return ValidationCheck(
                id="V1.2",
                name="V1.2_no_empty_tokens",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Empty/whitespace-only tokens: {empty_tokens}",
                details={"empty_token_ids": empty_tokens},
            )

        return ValidationCheck(
            id="V1.2",
            name="V1.2_no_empty_tokens",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message="All tokens have non-empty text",
        )

    def _check_metadata_completeness(self, data: Stage1Output) -> ValidationCheck:
        """V1.3: Every token must have a metadata entry and vice versa."""
        token_keys = set(data.tokens.keys())
        metadata_keys = set(data.metadata.keys())

        missing_metadata = token_keys - metadata_keys
        extra_metadata = metadata_keys - token_keys

        if missing_metadata or extra_metadata:
            details = {}
            message_parts = []
            if missing_metadata:
                details["missing_metadata"] = sorted(missing_metadata)
                message_parts.append(f"Tokens without metadata: {sorted(missing_metadata)}")
            if extra_metadata:
                details["extra_metadata"] = sorted(extra_metadata)
                message_parts.append(f"Metadata without tokens: {sorted(extra_metadata)}")

            return ValidationCheck(
                id="V1.3",
                name="V1.3_metadata_completeness",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="; ".join(message_parts),
                details=details,
            )

        return ValidationCheck(
            id="V1.3",
            name="V1.3_metadata_completeness",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message=f"Metadata complete for {len(token_keys)} tokens",
        )

    def _check_no_overlapping_ranges(self, data: Stage1Output) -> ValidationCheck:
        """V1.4: No two tokens may have overlapping character ranges."""
        if not data.metadata:
            return ValidationCheck(
                id="V1.4",
                name="V1.4_no_overlapping_ranges",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
                message="No metadata to validate",
            )

        sorted_ids = sorted(data.metadata.keys(), key=lambda x: int(x[1:]))
        overlaps = []

        for i in range(len(sorted_ids) - 1):
            current_meta = data.metadata[sorted_ids[i]]
            next_meta = data.metadata[sorted_ids[i + 1]]
            if current_meta.char_end > next_meta.char_start:
                overlaps.append({
                    "token_a": sorted_ids[i],
                    "token_a_end": current_meta.char_end,
                    "token_b": sorted_ids[i + 1],
                    "token_b_start": next_meta.char_start,
                    "overlap_chars": current_meta.char_end - next_meta.char_start,
                })

        if overlaps:
            return ValidationCheck(
                id="V1.4",
                name="V1.4_no_overlapping_ranges",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"{len(overlaps)} overlapping range(s) detected",
                details={"overlaps": overlaps},
            )

        return ValidationCheck(
            id="V1.4",
            name="V1.4_no_overlapping_ranges",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message="No overlapping character ranges",
        )

    def _check_full_coverage(self, data: Stage1Output) -> ValidationCheck:
        """V1.5: All source characters must be accounted for by tokens.

        When include_whitespace=False, gaps that are purely whitespace are
        expected and produce a WARNING. Non-whitespace gaps are CRITICAL.
        When include_whitespace=True, any gap is CRITICAL.
        """
        if not data.source_text:
            return ValidationCheck(
                id="V1.5",
                name="V1.5_full_coverage",
                passed=True,
                severity=ValidationSeverity.WARNING,
                message="Empty source text",
            )

        if not data.metadata:
            # No tokens but non-empty source — complete miss
            return ValidationCheck(
                id="V1.5",
                name="V1.5_full_coverage",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"No tokens cover source text ({len(data.source_text)} chars)",
                details={"source_length": len(data.source_text), "covered": 0},
            )

        sorted_ids = sorted(data.metadata.keys(), key=lambda x: int(x[1:]))

        # Check coverage
        gaps = []
        cursor = 0

        # Leading gap
        first_meta = data.metadata[sorted_ids[0]]
        if first_meta.char_start > 0:
            gap_text = data.source_text[:first_meta.char_start]
            gaps.append({
                "start": 0,
                "end": first_meta.char_start,
                "text": gap_text,
                "is_whitespace": gap_text.isspace(),
            })

        # Between-token gaps
        for i in range(len(sorted_ids) - 1):
            current_meta = data.metadata[sorted_ids[i]]
            next_meta = data.metadata[sorted_ids[i + 1]]
            if next_meta.char_start > current_meta.char_end:
                gap_text = data.source_text[current_meta.char_end:next_meta.char_start]
                gaps.append({
                    "start": current_meta.char_end,
                    "end": next_meta.char_start,
                    "text": gap_text,
                    "is_whitespace": gap_text.isspace(),
                })

        # Trailing gap
        last_meta = data.metadata[sorted_ids[-1]]
        if last_meta.char_end < len(data.source_text):
            gap_text = data.source_text[last_meta.char_end:]
            gaps.append({
                "start": last_meta.char_end,
                "end": len(data.source_text),
                "text": gap_text,
                "is_whitespace": gap_text.isspace(),
            })

        if not gaps:
            return ValidationCheck(
                id="V1.5",
                name="V1.5_full_coverage",
                passed=True,
                severity=ValidationSeverity.WARNING,
                message=f"Full coverage: all {len(data.source_text)} characters accounted for",
            )

        # Classify gaps
        whitespace_gaps = [g for g in gaps if g["is_whitespace"]]
        non_whitespace_gaps = [g for g in gaps if not g["is_whitespace"]]

        include_ws = data.config.include_whitespace if data.config else True

        if non_whitespace_gaps:
            # Non-whitespace gaps are always CRITICAL
            return ValidationCheck(
                id="V1.5",
                name="V1.5_full_coverage",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Non-whitespace gaps detected: {len(non_whitespace_gaps)} gap(s) with content",
                details={
                    "non_whitespace_gaps": non_whitespace_gaps,
                    "whitespace_gaps": len(whitespace_gaps),
                },
            )

        if include_ws:
            # include_whitespace=True but gaps exist → CRITICAL
            return ValidationCheck(
                id="V1.5",
                name="V1.5_full_coverage",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Whitespace gaps detected with include_whitespace=True: {len(gaps)} gap(s)",
                details={"gaps": gaps},
            )

        # include_whitespace=False and only whitespace gaps → WARNING
        return ValidationCheck(
            id="V1.5",
            name="V1.5_full_coverage",
            passed=False,
            severity=ValidationSeverity.WARNING,
            message=f"Whitespace gaps expected (include_whitespace=False): {len(gaps)} gap(s), {sum(len(g['text']) for g in gaps)} chars",
            details={"whitespace_gaps": gaps, "total_gap_chars": sum(len(g["text"]) for g in gaps)},
        )

    def name(self) -> str:
        return "ValidationV1"
