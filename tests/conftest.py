"""Test helpers for pytest"""
from unittest.mock import patch

import pytest

from .const import TEST_V4_PATH


@pytest.fixture(autouse=True)
def mock_url():
    """Create 'mock_url' argument for test cases"""
    with patch("pytomorrowio.TomorrowioV4._get_url", return_value=TEST_V4_PATH):
        yield
