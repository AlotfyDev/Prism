"""Unit tests for MetadataIndexer (P1.3)."""

import pytest

from prism.schemas import Stage1Input, Stage1Output, TokenizationConfig
from prism.stage1.metadata import MetadataIndexer


class TestMetadataIndexerInstantiation:
    """Tests for MetadataIndexer construction."""

    def test_can_instantiate(self):
        builder = MetadataIndexer()
        assert isinstance(builder.name(), str)

    def test_name_is_descriptive(self):
        builder = MetadataIndexer()
        assert "metadata" in builder.name().lower()

    def test_tier_is_python_nlp(self):
        builder = MetadataIndexer()
        assert builder.tier == "python_nlp"


class TestMetadataIndexerValidateInput:
    """Tests for input validation."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_valid_raw_text(self):
        inp = Stage1Input(source="hello world", source_type="raw_text")
        assert self.indexer.validate_input(inp) == (True, "")

    def test_empty_raw_text_fails(self):
        inp = Stage1Input(source="", source_type="raw_text")
        ok, msg = self.indexer.validate_input(inp)
        assert ok is False
        assert msg != ""

    def test_valid_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello", encoding="utf-8")
        inp = Stage1Input(source=str(f), source_type="file")
        assert self.indexer.validate_input(inp) == (True, "")

    def test_missing_file_fails(self, tmp_path):
        inp = Stage1Input(source=str(tmp_path / "no.md"), source_type="file")
        ok, msg = self.indexer.validate_input(inp)
        assert ok is False


class TestMetadataIndexerValidateOutput:
    """Tests for output validation."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_none_output_fails(self):
        ok, msg = self.indexer.validate_output(None)
        assert ok is False
        assert msg != ""

    def test_wrong_type_fails(self):
        ok, msg = self.indexer.validate_output("not a model")
        assert ok is False

    def test_metadata_key_mismatch_fails(self):
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={"T1": {"token_id": "T1", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello",
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is False
        assert "missing metadata" in msg.lower()

    def test_missing_metadata_fails(self):
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}, "T1": {"id": "T1", "text": "world"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1}},
            source_text="hello world",
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is False
        assert "missing metadata" in msg.lower()

    def test_extra_metadata_fails(self):
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello",
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is False
        assert "metadata keys without matching" in msg.lower()

    def test_invalid_char_range_fails_pydantic(self):
        """Pydantic rejects char_end < char_start at construction time."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            Stage1Output(
                tokens={"T0": {"id": "T0", "text": "hello"}},
                metadata={"T0": {"token_id": "T0", "char_start": 5, "char_end": 2, "source_line": 1}},
                source_text="hello",
            )

    def test_range_out_of_bounds_fails(self):
        output = Stage1Output(
            tokens={"T0": {"id": "T0", "text": "hello"}},
            metadata={"T0": {"token_id": "T0", "char_start": 0, "char_end": 20, "source_line": 1}},
            source_text="hello",
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is False
        assert "out of bounds" in msg.lower()

    def test_token_text_mismatch_fails(self):
        """Token text must match source at recorded position."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "lo wo"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 10, "source_line": 1},
            },
            source_text="hello world",
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is False
        assert "mismatch" in msg.lower()

    def test_overlapping_ranges_fails(self):
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": " world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 7, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 3, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
        )
        ok, msg = self.indexer.validate_output(output)
        # Text mismatch catches it first since positions are wrong
        assert ok is False

    def test_gap_detection_fails_with_whitespace(self):
        """Non-whitespace gap between tokens fails even with include_whitespace=True."""
        # source: "hello world" — gap is "llo" (positions 2-5) which is non-whitespace
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "he"},
                "T1": {"id": "T1", "text": " "},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 2, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 6, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
            config=TokenizationConfig(include_whitespace=True),
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is False
        assert "gap" in msg.lower()

    def test_valid_output_passes(self):
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": " "},
                "T2": {"id": "T2", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 5, "char_end": 6, "source_line": 1},
                "T2": {"token_id": "T2", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is True
        assert msg == ""

    def test_semantic_only_with_config_passes(self):
        """Semantic tokens without whitespace pass when config says include_whitespace=False."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
            config=TokenizationConfig(include_whitespace=False),
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is True
        assert msg == ""

    def test_semantic_only_without_config_fails(self):
        """Semantic tokens without whitespace fail when config is absent (defaults to strict)."""
        output = Stage1Output(
            tokens={
                "T0": {"id": "T0", "text": "hello"},
                "T1": {"id": "T1", "text": "world"},
            },
            metadata={
                "T0": {"token_id": "T0", "char_start": 0, "char_end": 5, "source_line": 1},
                "T1": {"token_id": "T1", "char_start": 6, "char_end": 11, "source_line": 1},
            },
            source_text="hello world",
        )
        ok, msg = self.indexer.validate_output(output)
        assert ok is False
        assert "gap" in msg.lower()


class TestMetadataIndexerProcess:
    """Tests for the process() method."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_single_word(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="hello", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.token_count == 1
        assert "T0" in output.tokens
        assert output.tokens["T0"].text == "hello"

    def test_two_words(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.token_count == 2
        assert output.tokens["T0"].text == "hello"
        assert output.tokens["T1"].text == "world"

    def test_punctuation_separate_tokens(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="Hi.", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        texts = [t.text for t in output.tokens.values()]
        assert "Hi" in texts
        assert "." in texts

    def test_metadata_created_for_each_token(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert len(output.metadata) == len(output.tokens)
        assert set(output.metadata.keys()) == set(output.tokens.keys())

    def test_valid_output_passes_validation(self):
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="hello world", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        ok, msg = self.indexer.validate_output(output)
        assert ok is True
        assert msg == ""

    def test_char_positions_accurate(self):
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="abc def", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.metadata["T0"].char_start == 0
        assert output.metadata["T0"].char_end == 3
        assert output.metadata["T1"].char_start == 3
        assert output.metadata["T1"].char_end == 4

    def test_global_sequential_ids(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="one two three", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        ids = sorted(output.tokens.keys(), key=lambda x: int(x[1:]))
        assert ids == [f"T{i}" for i in range(len(ids))]

    def test_source_text_preserved(self):
        original = "test content here"
        config = TokenizationConfig()
        inp = Stage1Input(source=original, source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.source_text == original

    def test_returns_stage1_output(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="test", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert isinstance(output, Stage1Output)


class TestMetadataIndexerMultiParagraph:
    """Multi-paragraph metadata tests."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_multi_paragraph_tokenized(self):
        config = TokenizationConfig()
        text = "First para.\n\nSecond para."
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.token_count > 0
        texts = [t.text for t in output.tokens.values()]
        assert "First" in texts
        assert "Second" in texts

    def test_source_line_tracks_paragraphs(self):
        config = TokenizationConfig()
        text = "line one\nline two"
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        lines = {m.source_line for m in output.metadata.values()}
        assert 1 in lines
        assert 2 in lines

    def test_whitespace_includes_newlines(self):
        config = TokenizationConfig(include_whitespace=True)
        text = "hi\nbye"
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        texts = [t.text for t in output.tokens.values()]
        assert "\n" in texts
        ok, msg = self.indexer.validate_output(output)
        assert ok is True


class TestMetadataIndexerMarkdown:
    """Markdown-specific metadata tests."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_heading_tokenized(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="# Title", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        texts = [t.text for t in output.tokens.values()]
        assert "#" in texts
        assert "Title" in texts

    def test_list_items_tokenized(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="- item\n- two", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.token_count > 0
        texts = [t.text for t in output.tokens.values()]
        assert "-" in texts


class TestMetadataIndexerWhitespace:
    """Whitespace handling tests."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_exclude_whitespace_by_default(self):
        config = TokenizationConfig(include_whitespace=False)
        inp = Stage1Input(source="a b", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert " " not in [t.text for t in output.tokens.values()]

    def test_include_whitespace(self):
        config = TokenizationConfig(include_whitespace=True)
        inp = Stage1Input(source="a b", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert " " in [t.text for t in output.tokens.values()]
        ok, msg = self.indexer.validate_output(output)
        assert ok is True


class TestMetadataIndexerKnownOffsets:
    """Tests with known text → known offsets (acceptance criterion)."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_known_single_token(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="hello", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        meta = output.metadata["T0"]
        assert meta.char_start == 0
        assert meta.char_end == 5
        assert meta.source_line == 1

    def test_known_two_tokens(self):
        config = TokenizationConfig()
        inp = Stage1Input(source="ab cd", source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.metadata["T0"].char_start == 0
        assert output.metadata["T0"].char_end == 2
        assert output.metadata["T1"].char_start == 3
        assert output.metadata["T1"].char_end == 5

    def test_known_multiline(self):
        config = TokenizationConfig()
        text = "AB\nCD"
        inp = Stage1Input(source=text, source_type="raw_text", config=config)
        output = self.indexer.process(inp, config)
        assert output.metadata["T0"].char_start == 0
        assert output.metadata["T0"].char_end == 2
        assert output.metadata["T0"].source_line == 1
        assert output.metadata["T1"].char_start == 3
        assert output.metadata["T1"].char_end == 5
        assert output.metadata["T1"].source_line == 2


class TestMetadataIndexerFile:
    """File-based metadata tests."""

    def setup_method(self):
        self.indexer = MetadataIndexer()

    def test_from_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello world", encoding="utf-8")
        config = TokenizationConfig()
        inp = Stage1Input(source=str(f), source_type="file", config=config)
        output = self.indexer.process(inp, config)
        assert output.token_count == 2

    def test_file_not_found(self, tmp_path):
        config = TokenizationConfig()
        inp = Stage1Input(source=str(tmp_path / "no.md"), source_type="file", config=config)
        with pytest.raises(ValueError, match="Invalid input"):
            self.indexer.process(inp, config)

    def test_file_unicode(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("café naïve", encoding="utf-8")
        config = TokenizationConfig()
        inp = Stage1Input(source=str(f), source_type="file", config=config)
        output = self.indexer.process(inp, config)
        assert output.token_count > 0


class TestMetadataIndexerEdgeCases:
    """Edge case tests."""

    def setup_method(self):
        self.indexer = MetadataIndexer()
        self.config = TokenizationConfig()

    def test_lemma_populated(self):
        inp = Stage1Input(source="running", source_type="raw_text", config=self.config)
        output = self.indexer.process(inp, self.config)
        assert output.tokens["T0"].lemma is not None

    def test_pos_populated(self):
        inp = Stage1Input(source="hello", source_type="raw_text", config=self.config)
        output = self.indexer.process(inp, self.config)
        assert output.tokens["T0"].pos is not None

    def test_empty_string_fails_validation(self):
        inp = Stage1Input(source="", source_type="raw_text", config=self.config)
        ok, _ = self.indexer.validate_input(inp)
        assert ok is False

    def test_newlines_only_fails_validation(self):
        inp = Stage1Input(source="\n\n", source_type="raw_text", config=self.config)
        ok, _ = self.indexer.validate_input(inp)
        assert ok is False


class TestMetadataIndexerVersion:
    """Tests for version property."""

    def test_version_is_string(self):
        assert isinstance(MetadataIndexer().version, str)

    def test_version_format(self):
        assert MetadataIndexer().version.startswith("v")
