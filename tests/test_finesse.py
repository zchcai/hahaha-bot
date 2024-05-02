"""Unit Tests for HanabiClient."""

import unittest

from unittest.mock import patch, MagicMock

# Imports (local application)
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.hanabi_client import HanabiClient
from src.game_state import GameState
from src.utils import dump

# Fake helpful constants.
FAKE_TABLE_ID = 42

# Helper functions
def get_default_game_state():
    state = GameState()
    state.current_player_index = 0
    state.our_player_index = 0
    state.clue_tokens = 8
    state.play_stacks = [0, 0, 0, 0, 0]
    state.player_names = ['Alice', 'Bob', 'Charles', 'David']
    # https://hanab.live/replay/1124590#1
    # (This is my first online game :)
    state.player_hands = [
        # Player 0 (self)
        [
            Card(order=0),  # discard slot
            Card(order=1),
            Card(order=2),
            Card(order=3)   # draw slot
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
    return state

def get_default_client(game_state: GameState=None):
    client = HanabiClient("some_uri", "some_cookie")
    client.current_table_id = FAKE_TABLE_ID
    if game_state is None:
        client.games[FAKE_TABLE_ID] = get_default_game_state()
    else:
        client.games[FAKE_TABLE_ID] = game_state
    client.send = MagicMock()
    return client

# Test class.
class TestHandleAction(unittest.TestCase):
    """Class to test handle_action() function."""
    mock_ws_instance = MagicMock()
    
    @patch('websocket.WebSocketApp')
    def test_basic_one_card_finesse(self, mock_websocketapp):
        """Basic finesse."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        client = get_default_client(state)

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.COLOR_CLUE.value, 'target': 1, 'value': 3} # TODO: target should be 3
        )

if __name__ == '__main__':
    unittest.main()
