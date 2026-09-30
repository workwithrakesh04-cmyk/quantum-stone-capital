"""Tests for strategies_py.loader."""
from strategies_py.loader import load_all_strategies, _STRATEGY_MODULES
from strategies_py.base import BaseStrategy


def test_loader_returns_list():
    classes = load_all_strategies()
    assert isinstance(classes, list)


def test_loader_all_are_base_strategy_subclasses():
    classes = load_all_strategies()
    for c in classes:
        assert issubclass(c, BaseStrategy)


def test_loader_handles_missing_modules():
    # Before 5a-2 lands, most strategy modules don't exist.
    # Loader must not raise - should return whatever is available (possibly empty).
    classes = load_all_strategies()
    # At minimum, no exception was raised
    assert classes is not None

    # The module list should be populated for future deliveries
    assert len(_STRATEGY_MODULES) >= 38
