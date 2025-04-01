import unittest

from src.card import Card
from src.constants import ACTION
from src.conventions import evaluate
from src.snapshot import Snapshot


# Helper functions
def _get_2p_default_snapshot():
    snapshot = Snapshot()
    snapshot.initialize(
        num_players=2,
        start_player_index=0,
        hands=[
            [
                # Player 0 (self)
                Card(order=0),  # discard slot
                Card(order=1),
                Card(order=2),
                Card(order=3),
                Card(order=4),  # draw slot
            ],
            [
                # Player 1
                Card(order=5, rank=3, suit_index=2),  # discard slot
                Card(order=6, rank=3, suit_index=2),
                Card(order=7, rank=1, suit_index=0),
                Card(order=8, rank=1, suit_index=0),
                Card(order=9, rank=1, suit_index=0),
            ],
        ],
    )
    return snapshot


def get_default_snapshot():
    snapshot = Snapshot()
    snapshot.initialize(
        num_players=4,
        start_player_index=0,
        # https://hanab.live/replay/1124590#1
        # (This is my first online game :)
        hands=[
            [
                # Player 0 (self)
                Card(order=0),  # discard slot
                Card(order=1),
                Card(order=2),
                Card(order=3),  # draw slot
            ],
            [
                # Player 1
                Card(order=4, rank=2, suit_index=2),  # discard slot
                Card(order=5, rank=3, suit_index=4),
                Card(order=6, rank=2, suit_index=2),
                Card(order=7, rank=1, suit_index=3),  # draw slot
            ],
            [
                # Player 2
                Card(order=8, rank=1, suit_index=0),  # discard slot
                Card(order=9, rank=1, suit_index=0),
                Card(order=10, rank=2, suit_index=0),
                Card(order=11, rank=4, suit_index=4),  # draw slot
            ],
            [
                # Player 3
                Card(order=12, rank=1, suit_index=2),  # discard slot
                Card(order=13, rank=2, suit_index=3),
                Card(order=14, rank=1, suit_index=1),
                Card(order=15, rank=3, suit_index=0),  # draw slot
            ],
        ],
    )
    return snapshot


# Test class.
class TestConventions(unittest.TestCase):
    """Class to test helper functions in Snapshot."""

    def test_evaluate(self):
        s = get_default_snapshot()

        actions = evaluate(s, viewer_index=0, player_index=0, remaining_search_level=1)

        assert len(actions) == 14

    def test_evaluate_no_normal_applicable_actions(self):
        s = _get_2p_default_snapshot()

        actions = evaluate(s, viewer_index=0, player_index=0, remaining_search_level=1)

        assert len(actions) == 0
