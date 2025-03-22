import unittest

from src.card import Card
from src.conventions import evaluate
from src.snapshot import Snapshot


# Helper functions
def get_default_snapshot():
    snapshot = Snapshot()
    snapshot.initialize(
        num_players=4,
        start_player_index=0,
    # https://hanab.live/replay/1124590#1
    # (This is my first online game :)
        hands = [[
        # Player 0 (self)
            Card(order=0),  # discard slot
            Card(order=1),
            Card(order=2),
            Card(order=3),  # draw slot
        ], [
        # Player 1
            Card(order=4, rank=2, suit_index=2),    # discard slot
            Card(order=5, rank=3, suit_index=4),
            Card(order=6, rank=2, suit_index=2),
            Card(order=7, rank=1, suit_index=3),    # draw slot
        ], [
        # Player 2
            Card(order=8, rank=1, suit_index=0),    # discard slot
            Card(order=9, rank=1, suit_index=0),
            Card(order=10, rank=2, suit_index=0),
            Card(order=11, rank=4, suit_index=4),    # draw slot
        ], [
        # Player 3
            Card(order=12, rank=1, suit_index=2),    # discard slot
            Card(order=13, rank=2, suit_index=3),
            Card(order=14, rank=1, suit_index=1),
            Card(order=15, rank=3, suit_index=0),    # draw slot
        ]])
    return snapshot

# Test class.
class TestSnapshot(unittest.TestCase):
    """Class to test helper functions in Snapshot."""

    def test_call_llm(self):
        s = get_default_snapshot()

        game_valid_actions = s.get_valid_actions(0, 0)
        actions = evaluate(s, 0, 0)

        assert(len(actions) == len(game_valid_actions))
