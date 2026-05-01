"""BDD step definitions for Stage 1 Tokenization behavioral tests.

Implements all Given/When/Then steps for stage1_tokenization.feature,
testing the real-world behavior of:
- MetadataIndexer (tokenization + metadata validation)
- ValidationV1 (token integrity gate)

Tests use actual spaCy tokenization on realistic Markdown documents,
not synthetic data. This is behavioral testing — verifying the system
does what users expect in real contexts.
"""

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

from prism.schemas import Stage1Input, Stage1Output, TokenizationConfig
from prism.core.validation_unit import ValidationSeverity


# --- Load all scenarios from the feature file ---
scenarios("stage1_tokenization.feature")


# ========================
# Shared context for BDD scenarios
# ========================

@pytest.fixture(scope="function")
def bdd_ctx():
    """Per-scenario shared context dictionary."""
    return {}


# ========================
# Given steps
# ========================

@given("a Markdown document with known content", target_fixture="bdd_ctx")
def markdown_known_content(bdd_ctx):
    bdd_ctx["doc_text"] = "The quick brown fox jumps over the lazy dog."
    return bdd_ctx


@given("a Markdown document", target_fixture="bdd_ctx")
def markdown_document(bdd_ctx):
    bdd_ctx["doc_text"] = "The quick brown fox jumps over the lazy dog."
    bdd_ctx["min_tokens"] = 9
    return bdd_ctx


@given("a single_paragraph document", target_fixture="bdd_ctx")
def doc_single_paragraph(bdd_ctx):
    bdd_ctx["doc_text"] = "The quick brown fox jumps over the lazy dog."
    bdd_ctx["min_tokens"] = 9
    return bdd_ctx


@given("a multi_paragraph document", target_fixture="bdd_ctx")
def doc_multi_paragraph(bdd_ctx):
    bdd_ctx["doc_text"] = (
        "First paragraph introduces the topic.\n\n"
        "Second paragraph expands on the details.\n\n"
        "Third paragraph concludes the argument."
    )
    bdd_ctx["min_tokens"] = 15
    return bdd_ctx


@given("a with_lists document", target_fixture="bdd_ctx")
def doc_with_lists(bdd_ctx):
    bdd_ctx["doc_text"] = (
        "- Item one\n"
        "- Item two\n"
        "- Item three\n"
        "  - Sub item A\n"
        "  - Sub item B"
    )
    bdd_ctx["min_tokens"] = 10
    return bdd_ctx


@given("a with_tables document", target_fixture="bdd_ctx")
def doc_with_tables(bdd_ctx):
    bdd_ctx["doc_text"] = (
        "| Name | Age | City |\n"
        "|------|-----|------|\n"
        "| Alice | 30 | NYC |\n"
        "| Bob | 25 | LA |"
    )
    bdd_ctx["min_tokens"] = 12
    return bdd_ctx


@given("a with_code_blocks document", target_fixture="bdd_ctx")
def doc_with_code_blocks(bdd_ctx):
    bdd_ctx["doc_text"] = (
        "Here is some code:\n\n"
        "```python\n"
        "def hello():\n"
        "    print('world')\n"
        "```\n\n"
        "And more text after."
    )
    bdd_ctx["min_tokens"] = 10
    return bdd_ctx


@given("a mixed_layers document", target_fixture="bdd_ctx")
def doc_mixed_layers(bdd_ctx):
    bdd_ctx["doc_text"] = (
        "# Analysis Report\n\n"
        "This report examines the data.\n\n"
        "## Key Findings\n\n"
        "- Finding one is significant.\n"
        "- Finding two supports the hypothesis.\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| Accuracy | 0.95 |\n\n"
        "```python\n"
        "result = analyze(data)\n"
        "```\n\n"
        "See footnote for details."
    )
    bdd_ctx["min_tokens"] = 30
    return bdd_ctx


@given("valid Stage1Output", target_fixture="bdd_ctx")
def valid_stage1_output(bdd_ctx):
    from prism.stage1.metadata import MetadataIndexer

    indexer = MetadataIndexer()
    config = TokenizationConfig(include_whitespace=True)
    inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
    bdd_ctx["valid_output"] = indexer.process(inp, config)
    return bdd_ctx


# ========================
# When steps
# ========================

@when("the document is tokenized", target_fixture="bdd_ctx")
def tokenize_document(bdd_ctx):
    from prism.stage1.metadata import MetadataIndexer

    text = bdd_ctx.get("doc_text")
    assert text is not None, "Document must be set first"

    indexer = MetadataIndexer()
    config = TokenizationConfig(include_whitespace=True)
    inp = Stage1Input(source=text, source_type="raw_text", config=config)
    output = indexer.process(inp, config)

    bdd_ctx["tokenized_output"] = output
    bdd_ctx["output_tokens"] = list(output.tokens.keys())
    bdd_ctx["output_count"] = output.token_count
    bdd_ctx["source_text"] = output.source_text
    return bdd_ctx


@when("metadata is computed for each token", target_fixture="bdd_ctx")
def compute_metadata(bdd_ctx):
    from prism.stage1.metadata import MetadataIndexer

    # Use existing tokenized output if available
    output = bdd_ctx.get("tokenized_output")
    if output is None:
        indexer = MetadataIndexer()
        config = TokenizationConfig(include_whitespace=True)
        text = bdd_ctx.get("doc_text") or "hello world"
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = indexer.process(inp, config)
        bdd_ctx["tokenized_output"] = output
        bdd_ctx["output_tokens"] = list(output.tokens.keys())
        bdd_ctx["output_count"] = output.token_count
        bdd_ctx["source_text"] = output.source_text

    bdd_ctx["metadata_output"] = output
    bdd_ctx["metadata_count"] = len(output.metadata)
    if "output_count" not in bdd_ctx:
        bdd_ctx["output_count"] = output.token_count
    return bdd_ctx


@when("ValidationV1 runs", target_fixture="bdd_ctx")
def run_validation_v1(bdd_ctx):
    from prism.stage1.validation_v1 import ValidationV1

    valid_output = bdd_ctx.get("valid_output")
    assert valid_output is not None, "Valid output must be set first"

    validator = ValidationV1()
    report = validator.validate(valid_output)
    bdd_ctx["validation_report"] = report
    bdd_ctx["report_passed"] = report.passed
    bdd_ctx["report_critical"] = len(report.critical_failures)
    bdd_ctx["report_checks"] = len(report.checks)
    return bdd_ctx


# ========================
# Then steps
# ========================

@then("token IDs should be sequential: T0, T1, T2, ...")
def check_sequential_ids(bdd_ctx):
    token_ids = bdd_ctx.get("output_tokens")
    assert token_ids is not None, "Tokenization must run first"
    token_ids = sorted(token_ids, key=lambda x: int(x[1:]))
    expected = [f"T{i}" for i in range(len(token_ids))]
    assert token_ids == expected, f"Expected {expected}, got {token_ids}"


@then("there should be no gaps in the sequence")
def check_no_gaps(bdd_ctx):
    token_ids = bdd_ctx.get("output_tokens")
    assert token_ids is not None, "Tokenization must run first"
    ids = [int(tid[1:]) for tid in token_ids]
    expected = list(range(max(ids) + 1))
    assert sorted(ids) == expected, f"Gap detected: expected {expected}, got {sorted(ids)}"


@then("token count should match the expected number")
def check_token_count(bdd_ctx):
    count = bdd_ctx.get("output_count")
    min_expected = bdd_ctx.get("min_tokens") or 1
    assert count is not None, "Tokenization must run first"
    assert count >= min_expected, f"Expected at least {min_expected} tokens, got {count}"


@then("every token should have char_start and char_end")
def check_metadata_completeness(bdd_ctx):
    metadata_count = bdd_ctx.get("metadata_count")
    token_count = bdd_ctx.get("output_count")
    assert metadata_count is not None, "Metadata must be computed first"
    assert token_count is not None, "Tokenization must run first"
    assert metadata_count == token_count, (
        f"Metadata count ({metadata_count}) != token count ({token_count})"
    )


@then("char_end should be >= char_start")
def check_char_range_validity(bdd_ctx):
    output = bdd_ctx.get("metadata_output") or bdd_ctx.get("tokenized_output")
    assert output is not None, "Metadata must be computed first"

    for token_id, meta in output.metadata.items():
        assert meta.char_end >= meta.char_start, (
            f"{token_id}: char_end ({meta.char_end}) < char_start ({meta.char_start})"
        )


@then("no two tokens should have overlapping char ranges")
def check_no_overlaps(bdd_ctx):
    output = bdd_ctx.get("metadata_output") or bdd_ctx.get("tokenized_output")
    assert output is not None, "Metadata must be computed first"

    sorted_ids = sorted(output.metadata.keys(), key=lambda x: int(x[1:]))
    for i in range(len(sorted_ids) - 1):
        current = output.metadata[sorted_ids[i]]
        next_token = output.metadata[sorted_ids[i + 1]]
        assert current.char_end <= next_token.char_start, (
            f"Overlap: {sorted_ids[i]} (end={current.char_end}) overlaps "
            f"{sorted_ids[i + 1]} (start={next_token.char_start})"
        )


@then("all critical checks should pass")
def check_critical_pass(bdd_ctx):
    critical = bdd_ctx.get("report_critical")
    assert critical is not None, "Validation must run first"
    assert critical == 0, f"{critical} critical failures found"


@then("the validation report should have no critical failures")
def check_no_critical_failures(bdd_ctx):
    critical = bdd_ctx.get("report_critical")
    assert critical is not None, "Validation must run first"
    assert critical == 0


@then("the output should be valid Stage1Output")
def check_valid_output(bdd_ctx):
    count = bdd_ctx.get("output_count")
    source = bdd_ctx.get("source_text")
    assert count is not None, "Tokenization must run first"
    assert isinstance(count, int)
    assert count > 0
    assert isinstance(source, str)
