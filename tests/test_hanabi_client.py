"""Unit Tests for HanabiClient."""

import unittest

from unittest.mock import patch, MagicMock

# Imports (local application)
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.hanabi_client import HanabiClient
from src.game_state import GameState

# Fake helpful constants.
FAKE_TABLE_ID = 42

# Test class.
class TestDecideAction(unittest.TestCase):
    """Class to test decide_action() function."""
   
    @patch('websocket.WebSocketApp')
    def test_play_clued_playable_card(self, mock_websocketapp):
        """When negative information is sufficient to tell us to play."""

        # Setup: Create a MagicMock for the WebSocketApp instance.
        mock_ws_instance = MagicMock()
        mock_websocketapp.return_value = mock_ws_instance
        client = HanabiClient("some_uri", "some_cookie")
        client.current_table_id = FAKE_TABLE_ID
        client.send = MagicMock()
        state = GameState()
        state.play_stacks = [0, 1, 1, 1, 1]
        state.current_player_index = 0
        state.our_player_index = 0
        state.player_hands = [
            # Player 0 (self)
            [
                Card(order=0),
                Card(order=1),
                Card(order=2, clues = [Clue(hint_type=2, hint_value=0, classification=1)]),
                Card(order=3),
                Card(order=4),
            ],
            # Player 1 (the next player)
            [
                Card(order=5, rank=5, suit_index=1),
                Card(order=6, rank=2, suit_index=3),
                Card(order=7, rank=3, suit_index=4),
                Card(order=8, rank=4, suit_index=1),
                Card(order=9, rank=4, suit_index=0),
            ]
        ]
        client.games[FAKE_TABLE_ID] = state

        client.decide_action()

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY, 'target': 2})


    @patch('websocket.WebSocketApp')
    def test_play_deduced_playable_card(self, mock_websocketapp):
        """When negative information is sufficient to tell us to play."""

        # Setup: Create a MagicMock for the WebSocketApp instance.
        mock_ws_instance = MagicMock()
        mock_websocketapp.return_value = mock_ws_instance
        client = HanabiClient("some_uri", "some_cookie")
        client.current_table_id = FAKE_TABLE_ID
        client.send = MagicMock()
        state = GameState()
        state.play_stacks = [0, 1, 1, 1, 1]
        state.current_player_index = 0
        state.our_player_index = 0
        state.player_hands = [
            # Player 0 (self)
            [
                Card(order=0, negative_ranks=[2,3,4,5], negative_colors=[1,2,3,4]),
                Card(order=1),
                Card(order=2),
                Card(order=3),
                Card(order=4),
            ],
            # Player 1 (the next player)
            [
                Card(order=5, rank=5, suit_index=1),
                Card(order=6, rank=2, suit_index=3),
                Card(order=7, rank=3, suit_index=4),
                Card(order=8, rank=4, suit_index=1),
                Card(order=9, rank=4, suit_index=0),
            ]
        ]
        client.games[FAKE_TABLE_ID] = state

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY, 'target': 0})

    @patch('websocket.WebSocketApp')
    def test_discard_when_without_clue_tokens(self, mock_websocketapp):
        """When no clues is available (and no cards to play), discard."""

        # Setup: Create a MagicMock for the WebSocketApp instance.
        mock_ws_instance = MagicMock()
        mock_websocketapp.return_value = mock_ws_instance
        client = HanabiClient("some_uri", "some_cookie")
        client.current_table_id = FAKE_TABLE_ID
        client.send = MagicMock()
        state = GameState()
        state.play_stacks = [0, 0, 0, 0, 0]
        state.clue_tokens = 0
        state.current_player_index = 0
        state.our_player_index = 0
        state.player_hands = [
            # Player 0 (self)
            [
                Card(order=0),  # discard slot
                Card(order=1),
                Card(order=2),
                Card(order=3),
                Card(order=4)   # draw slot
            ],
            # Player 1 (the next player)
            [
                Card(order=5, rank=5, suit_index=1),    # discard slot
                Card(order=6, rank=2, suit_index=3),
                Card(order=7, rank=3, suit_index=4),
                Card(order=8, rank=4, suit_index=1),
                Card(order=9, rank=4, suit_index=0),    # draw slot
            ]
        ]
        client.games[FAKE_TABLE_ID] = state

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.DISCARD, 'target': 0})

if __name__ == '__main__':
    unittest.main()
