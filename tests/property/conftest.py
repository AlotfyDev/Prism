"""Property-based test fixtures and Hypothesis strategies for Prism."""

import pytest
from hypothesis import settings, Verbosity
import hypothesis.strategies as st


# Hypothesis profile for CI vs local development
settings.register_profile("ci", max_examples=100, deadline=None)
settings.register_profile("dev", max_examples=20, deadline=None)
settings.register_profile("debug", max_examples=20, deadline=None, verbosity=Verbosity.verbose)

settings.load_profile("dev")


# --- Reusable Hypothesis Strategies ---


@st.composite
def non_empty_text(draw, min_chars=1, max_chars=200):
    """Strategy for generating non-empty text strings."""
    return draw(st.text(min_size=min_chars, max_size=max_chars).filter(lambda s: s.strip()))


@st.composite
def token_id(draw, max_tokens=500):
    """Strategy for generating valid token IDs (T0..TN)."""
    return f"T{draw(st.integers(min_value=0, max_value=max_tokens - 1))}"


@st.composite
def entity_id(draw, entity_types=None):
    """Strategy for generating valid entity IDs (E_{TYPE}_{N})."""
    if entity_types is None:
        entity_types = ["PERSON", "ORG", "LOC", "CONCEPT"]
    return f"E_{draw(st.sampled_from(entity_types))}_{draw(st.integers(min_value=0, max_value=99))}"


@st.composite
def confidence_score(draw):
    """Strategy for generating confidence scores in [0.0, 1.0]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


# --- Shared Fixtures ---


@pytest.fixture
def property_config():
    """Configuration for property-based tests.

    Override to customize max_examples, edge case generation, etc.
    """
    return {
        "max_examples": 20,
        "include_edge_cases": True,
        "edge_cases": ["", "single_token", "whitespace_only"],
    }
