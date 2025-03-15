"""Unit Tests for HanabiClient."""

import unittest

from unittest.mock import patch, MagicMock

# Imports (local application)
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.hanabi_client import HanabiClient
from src.game import Game
from src.utils import dump

# Fake helpful constants.
FAKE_TABLE_ID = 42

# Helper functions
def get_default_game_state():
    game = Game()
    game.our_player_index = 0
    game.clue_tokens = 8
    game.player_names = ['Alice', 'Bob', 'Charles', 'David']
    # https://hanab.live/replay/1124590#1
    # (This is my first online game :)
    game.player_hands = [
        # Player 0 (self)
        [
            Card(order=0),  # discard slot
            Card(order=1),
            Card(order=2),
            Card(order=3),  # draw slot
        ],
        # Player 1
        [
            Card(order=4, rank=2, suit_index=2),    # discard slot
            Card(order=5, rank=3, suit_index=4),
            Card(order=6, rank=2, suit_index=2),
            Card(order=7, rank=1, suit_index=3),    # draw slot
        ],
        # Player 2
        [
            Card(order=8, rank=1, suit_index=0),    # discard slot
            Card(order=9, rank=1, suit_index=0),
            Card(order=10, rank=2, suit_index=0),
            Card(order=11, rank=4, suit_index=4),    # draw slot
        ],
        # Player 3
        [
            Card(order=12, rank=1, suit_index=2),    # discard slot
            Card(order=13, rank=2, suit_index=3),
            Card(order=14, rank=1, suit_index=1),
            Card(order=15, rank=3, suit_index=0),    # draw slot
        ]
    ]
    return game

# Test class.
class TestGame(unittest.TestCase):
    """Class to test action predications and handling."""

    def test_basic_one_card_finesse(self):
        """Basic finesse."""

        game = get_default_game_state()

        actions = game.pre_action_intention_check()

        assert(len(actions) > 0)

if __name__ == '__main__':
    unittest.main()
