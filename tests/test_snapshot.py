import unittest

# Imports (local application)
from src.action import Action
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.snapshot import Snapshot
from src.utils import dump

# Fake helpful constants.
FAKE_TABLE_ID = 42

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

    def test_get_valid_actions(self):
        s = get_default_snapshot()

        actions = s.get_valid_actions(viewer_index=0, player_index=0)

        dump(actions)
        assert(len(actions) == 22)

    def test_get_valid_actions_no_clues(self):
        s = get_default_snapshot()
        s.clue_tokens = 0

        actions = s.get_valid_actions(viewer_index=0, player_index=0)

        dump(actions)
        assert(len(actions) == 8)

    def test_get_valid_actions_predict_other_player(self):
        s = get_default_snapshot()
        s = s.next_snapshot(Action(
            action_type=ACTION.COLOR_CLUE.value,
            player_index=0,
            clue=Clue(
                hint_type=ACTION.COLOR_CLUE.value,
                giver_index=0,
                receiver_index=3,
                hint_value=3,
            )
        ))

        actions = s.get_valid_actions(viewer_index=0, player_index=1)

        dump(actions)
        assert(len(actions) == 20)
    
    def test_is_end_status(self):
        s = get_default_snapshot()

        assert(not s.is_end_status())
    
    def test_is_end_status_boom_tokens_used_up(self):
        s = get_default_snapshot()
        s.boom_tokens = 0

        assert(s.is_end_status())
    
    def test_is_end_status_all_cards_played(self):
        s = get_default_snapshot()
        
        for i in range(5):
            for j in range(1, 6):
                s.play_pile.append(Card(rank=j, suit_index=i))
        
        assert(s.is_end_status())
    
    def test_is_end_status_cards_drawn(self):
        s = get_default_snapshot()
        s.num_remaining_cards = 0
        s.post_draw_turns = s.num_players

        assert(s.is_end_status())

if __name__ == '__main__':
    unittest.main()
