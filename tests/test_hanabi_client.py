"""Unit Tests for HanabiClient."""

import unittest

from unittest.mock import patch, MagicMock

# Imports (local application)
from src.card import Card
from src.constants import ACTION
from src.hanabi_client import HanabiClient
from src.game_state import GameState

# Test class.
class TestDecideAction(unittest.TestCase):
    """Class to test decide_action() function."""

    @patch('websocket.WebSocketApp')
    def test_discard_when_without_clue_tokens(self, mock_websocketapp):
        """When no clues is available (and no cards to play), discard."""

        # Setup: Create a MagicMock for the WebSocketApp instance.
        mock_ws_instance = MagicMock()
        mock_websocketapp.return_value = mock_ws_instance
        client = HanabiClient("some_uri", "some_cookie")
        client.current_table_id = 42
        client.send = MagicMock()
        state = GameState()
        state.clue_tokens = 0
        state.current_player_index = 0
        state.our_player_index = 0
        state.player_hands = [
            # Player 0 (self)
            [
                Card(order=5, rank=2, suit_index=3),    # discard slot
                Card(order=4, rank=3, suit_index=4),
                Card(order=3, rank=4, suit_index=1),
                Card(order=2, rank=4, suit_index=0),
                Card(order=1, rank=5, suit_index=2)     # draw slot
            ],
            # Player 1 (the next player)
            []
        ]
        client.games[42] = state

        client.decide_action(42)

        client.send.assert_called_once_with(
            'action',
            {'tableID': 42, 'type': ACTION.DISCARD, 'target': 5})

if __name__ == '__main__':
    unittest.main()
