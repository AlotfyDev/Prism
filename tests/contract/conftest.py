"""Contract test fixtures for Prism interface compliance tests."""

import pytest
from pydantic import BaseModel


@pytest.fixture
def processing_unit_contract():
    """Contract test configuration for ProcessingUnit implementations.

    Override this fixture in stage-specific tests to specify:
    - input_schema: The expected input type
    - output_schema: The expected output type
    - config_schema: The expected config type
    """
    return {
        "input_schema": BaseModel,
        "output_schema": BaseModel,
        "config_schema": BaseModel,
    }


@pytest.fixture
def validation_unit_contract():
    """Contract test configuration for ValidationUnit implementations.

    Override this fixture in stage-specific tests to specify:
    - expected_report_fields: Required fields on the ValidationReport
    """
    return {
        "expected_report_fields": ["stage", "passed", "timestamp", "checks"],
    }
