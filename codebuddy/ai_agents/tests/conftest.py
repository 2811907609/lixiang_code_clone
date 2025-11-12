"""
Pytest configuration and fixtures for ai_agents tests.
"""

import logging
import pytest


def pytest_configure(config):
    """Configure pytest and logging settings."""
    # Silence verbose debug logs from various libraries
    logging.getLogger('markdown_it').setLevel(logging.WARNING)
    # logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('smolagents').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    # Set root logger to INFO level to reduce noise
    logging.getLogger().setLevel(logging.INFO)


def pytest_collection_modifyitems(config, items):
    """
    自动为没有任何标记的测试添加unit标记
    """
    for item in items:
        # 如果测试项没有任何标记，则默认添加 'unit' 标记
        if not list(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Auto-configure logging for all tests."""
    # This fixture runs automatically for all tests
    logging.getLogger('markdown_it').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    yield
