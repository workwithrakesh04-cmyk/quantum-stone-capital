"""
Walk-forward cross-validation with purging and embargoing.
(Lopez de Prado, Advances in Financial Machine Learning.)
"""
from dataclasses import dataclass
from typing import Iterator, List


@dataclass
class WalkForwardSplit:
    train_idx: List[int]
    test_idx: List[int]


def walk_forward_splits(
    n_samples: int,
    train_size: int,
    test_size: int,
    step: int = None,
    purge: int = 0,
    embargo: int = 0,
) -> Iterator[WalkForwardSplit]:
    """
    Yield (train_idx, test_idx) splits walking forward through time.
    - purge: drop last `purge` training samples before test block
    - embargo: drop first `embargo` samples after test block
    """
    if step is None:
        step = test_size
    start = 0
    while start + train_size + purge + test_size + embargo <= n_samples:
        train_end = start + train_size
        if purge > 0:
            train_end = train_end - purge
        train_idx = list(range(start, train_end))
        test_start = start + train_size + purge
        test_end = test_start + test_size
        test_idx = list(range(test_start, test_end))
        yield WalkForwardSplit(train_idx=train_idx, test_idx=test_idx)
        start += step


def combinatorial_splits(
    n_samples: int,
    n_splits: int = 5,
    test_size: int = None,
) -> Iterator[WalkForwardSplit]:
    """Partition into n_splits; each block is a test set, rest is train."""
    if test_size is None:
        test_size = n_samples // n_splits
    for i in range(n_splits):
        test_start = i * test_size
        test_end = min(test_start + test_size, n_samples)
        test_idx = list(range(test_start, test_end))
        train_idx = [j for j in range(n_samples) if j not in test_idx]
        yield WalkForwardSplit(train_idx=train_idx, test_idx=test_idx)
