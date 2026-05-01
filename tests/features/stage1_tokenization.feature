Feature: Stage 1 — Holistic Tokenization

  As a pipeline operator
  I want to tokenize Markdown documents into a global sequential token stream
  So that every downstream stage can reference tokens by stable IDs (T0..TN)

  Background:
    Given a Markdown document with known content

  Scenario: Tokenizer produces sequential IDs with no gaps
    Given a Markdown document
    When the document is tokenized
    Then token IDs should be sequential: T0, T1, T2, ...
    And there should be no gaps in the sequence
    And token count should match the expected number

  Scenario: Metadata indexer maps correct char offsets
    Given a Markdown document
    When metadata is computed for each token
    Then every token should have char_start and char_end
    And char_end should be >= char_start
    And no two tokens should have overlapping char ranges

  Scenario: Token integrity validation passes on valid output
    Given valid Stage1Output
    When ValidationV1 runs
    Then all critical checks should pass
    And the validation report should have no critical failures

  Scenario Outline: Tokenizer handles <doc_type> documents
    Given a <doc_type> document
    When the document is tokenized
    Then the output should be valid Stage1Output

    Examples:
      | doc_type          |
      | single_paragraph  |
      | multi_paragraph   |
      | with_lists        |
      | with_tables       |
      | with_code_blocks  |
      | mixed_layers      |
