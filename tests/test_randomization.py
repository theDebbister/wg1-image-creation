"""Tests for randomization.py, rewritten with pytest.mark.parametrize.

The randomization functions were changed after the original tests were written.
is_break_time_allowed now returns (num_stimuli: int, break_allowed: bool).
The tests below document the *current* API behaviour and are parametrised to
cover edge cases efficiently.
"""
from __future__ import annotations

import pytest

from randomization import is_break_time_allowed, is_before_and_after_break, is_id_not_consecutive


# ---------------------------------------------------------------------------
# is_break_time_allowed
# ---------------------------------------------------------------------------

class TestIsBreakTimeAllowed:
    """is_break_time_allowed(pages) -> (num_stimuli, break_allowed: bool)

    The function walks the cumulative page sum, looking for the position
    closest to the midpoint.  A break is "allowed" only when that closest
    position falls at index 5, 6, or 7 (i.e. after 6, 7, or 8 stimuli).
    """

    @pytest.mark.parametrize("pages, expected_num, expected_allowed", [
        # Uniform. Break closest to midpoint at index 5 (cumulative 25 vs mid 25)
        ([5] * 10, 5, True),
        # Early heavy. Midpoint falls in the heavy block (index 3)
        ([10, 10, 10, 10, 5, 5, 5, 5, 5, 5], 3, False),
        # Late heavy. Index 5 is closest
        ([5, 5, 5, 5, 5, 5, 5, 5, 10, 5], 5, True),
        # Late heavy at index 7, closest, allowed
        ([5, 5, 5, 5, 5, 5, 5, 5, 11, 5], 6, True),
        # Heavy at index 1, not in {5,6,7}
        ([5, 11, 5, 5, 5, 5, 5, 5, 5, 5], 4, False),
        # Increasing sequence. Best at index 5
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 7, True),
    ])
    def test_break_position_and_allowed(self, pages, expected_num, expected_allowed):
        num, allowed = is_break_time_allowed(pages)
        assert num == expected_num
        assert allowed is expected_allowed

    def test_returns_tuple(self):
        result = is_break_time_allowed([5] * 10)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# is_before_and_after_break
# ---------------------------------------------------------------------------

class TestIsBeforeAndAfterBreak:

    @pytest.mark.parametrize("id_1, id_2, expected", [
        # Both in first half (before break at index 5 for [1..10])
        (1, 2, False),
        # 7 in first half (index 6), 10 in second half (index 9) → split by break
        (7, 10, True),
        # 2 in first half, 10 in second half → split
        (2, 10, True),
        # Both in second half
        (8, 10, False),
        # Symmetric
        (10, 2, True),
    ])
    def test_split_detection(self, id_1, id_2, expected):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert is_before_and_after_break(version, id_1, id_2) is expected


# ---------------------------------------------------------------------------
# is_id_not_consecutive
# ---------------------------------------------------------------------------

class TestIsIdNotConsecutive:

    @pytest.mark.parametrize("id_1, id_2, expected", [
        # Adjacent in first half, consecutive
        (2, 3, False),
        (5, 6, False),
        # Adjacent in second half, consecutive
        (8, 9, False),
        # Separated by break, not consecutive
        (1, 9, True),
        # Adjacent at start
        (1, 2, False),
        # 5 in first half, 9 in second, split by break
        (5, 9, True),
    ])
    def test_consecutive_detection(self, id_1, id_2, expected):
        version = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert is_id_not_consecutive(version, id_1, id_2) is expected
