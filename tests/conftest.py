"""Shared test fixtures for all Prism tests."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_markdown(fixtures_dir: Path) -> str:
    """Return content of a simple sample markdown file."""
    return (fixtures_dir / "sample_simple.md").read_text(encoding="utf-8")


@pytest.fixture
def empty_text() -> str:
    """Return empty string for edge case testing."""
    return ""


@pytest.fixture
def single_word_text() -> str:
    """Return single word text for minimal token testing."""
    return "hello"


@pytest.fixture
def multi_paragraph_text() -> str:
    """Return multi-paragraph text for comprehensive testing."""
    return """# Introduction

This is the first paragraph with several words.

## Analysis

The second paragraph discusses different concepts.

| Column A | Column B |
|----------|----------|
| data 1   | data 2   |

- List item one
- List item two
- List item three

Some `inline code` and more text.
"""
