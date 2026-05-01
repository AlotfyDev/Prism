"""Shared BDD step definitions for all Prism feature tests."""

import pytest
from pytest_bdd import given, when, then, parsers, scenarios


@pytest.fixture
def processing_unit():
    """Fixture for a processing unit instance. Override in stage-specific tests."""
    return None


@pytest.fixture
def validation_unit():
    """Fixture for a validation unit instance. Override in stage-specific tests."""
    return None


@pytest.fixture
def stage_output():
    """Fixture for stage output data. Override in stage-specific tests."""
    return None


@pytest.fixture
def validation_report():
    """Fixture for validation report. Override in stage-specific tests."""
    return None
