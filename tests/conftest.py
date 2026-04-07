"""Shared pytest hooks."""

import pytest

from logiclock.core.rule_usage import clear_rule_usage_sites


@pytest.fixture(autouse=True)
def _reset_rule_usage_sites() -> None:
    clear_rule_usage_sites()
    yield
    clear_rule_usage_sites()
