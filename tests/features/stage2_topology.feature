Feature: Stage 2 — Physical Topology Analysis

  As a pipeline operator
  I want to analyze the physical topology of Markdown documents
  So that every downstream stage can route to typed layer components with validated hierarchies

  Background:
    Given a Markdown document with known content

  Scenario: Parser produces AST with non-empty root nodes
    Given a Markdown document
    When the document is parsed into AST
    Then the AST should have at least one root node
    And every root node should have a valid NodeType

  Scenario: Classifier detects all layer types in mixed document
    Given a mixed_layers document with headings, paragraphs, lists, and code blocks
    When the AST is classified
    Then the report should contain heading instances
    And the report should contain paragraph instances
    And the report should contain list instances
    And the report should contain code_block instances

  Scenario: Classifier respects layer_types_to_detect filter
    Given a mixed_layers document
    When the AST is classified with HEADING-only filter
    Then the report should contain heading instances
    And the report should NOT contain paragraph instances
    And the report should NOT contain list instances

  Scenario: Hierarchy builder establishes correct parent-child relationships
    Given a document with heading containing paragraph
    When the classification report is built into hierarchy
    Then the hierarchy should have exactly one root node
    And the root node should have exactly one child
    And the child should be a PARAGRAPH instance

  Scenario: Component mapper produces typed components
    Given a document with table and list
    When the hierarchy is mapped to components
    Then the output should contain a TableComponent
    And the output should contain a ListComponent

  Scenario: Token span mapper links components to global token IDs
    Given a document with Stage1 tokens
    When components are mapped to token spans
    Then every component should have at least one token ID
    And token IDs should reference existing Stage1 tokens

  Scenario: Topology builder assembles valid Stage2Output
    Given mapped components with token mapping
    When the topology is assembled
    Then Stage2Output should have non-zero component count
    And every component should appear in component_to_tokens
    And layer_types should reflect all discovered layer types

  Scenario: Full pipeline produces validated output
    Given a realistic Markdown document
    When the full Stage 2 pipeline runs
    Then Stage2Output should be produced
    And ValidationV2 should pass all critical checks
    And the validation report should have no critical failures

  Scenario Outline: Pipeline handles <doc_type> documents
    Given a <doc_type> document
    When the full Stage 2 pipeline runs
    Then Stage2Output should be produced
    And ValidationV2 should not fail on critical checks

    Examples:
      | doc_type          |
      | single_heading    |
      | multi_heading     |
      | with_table        |
      | with_nested_list  |
      | with_code_blocks  |
      | with_blockquote   |
      | mixed_layers      |
      | complex_document  |

  Scenario: Nesting validation catches invalid parent-child relationships
    Given a classification report with invalid nesting
    When ValidationV2 runs on the assembled output
    Then the nesting check should flag the invalid relationship

  Scenario: Deterministic output for identical input
    Given a Markdown document
    When the full Stage 2 pipeline runs twice
    Then both outputs should have identical component counts
    And both outputs should have identical layer types
    And both outputs should have identical token mappings
