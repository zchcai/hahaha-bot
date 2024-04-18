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

# Helper functions
def get_default_game_state():
    state = GameState()
    state.current_player_index = 0
    state.our_player_index = 0
    state.clue_tokens = 8
    state.play_stacks = [0, 0, 0, 0, 0]
    state.player_names = ['Alice', 'Bob']
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
    # Setup: Create a MagicMock for the WebSocketApp instance.
    mock_ws_instance = MagicMock()

    @patch('websocket.WebSocketApp')
    def test_record_play_clue(self, mock_websocketapp):
        """When play clue is given."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_stacks = [0, 0, 0, 0, 1]
        state.current_player_index = 1
        client = get_default_client(state)

        data =  {'type': 'clue', 'clue': {'type': 0, 'value': 1}, 'giver': 1, 'list': [0, 3], 'target': 0, 'turn': 0}
        client.handle_action(data, FAKE_TABLE_ID)

        assert state.player_hands[0][3].clues == [Clue(hint_type=2, hint_value=1, giver_index=1, receiver_index=0, classification=1, turn=0)]
        assert state.player_hands[0][0].clues == [Clue(hint_type=2, hint_value=1, giver_index=1, receiver_index=0, classification=2, turn=0)]


# Test class.
class TestDecideAction(unittest.TestCase):
    """Class to test decide_action() function."""
    # Setup: Create a MagicMock for the WebSocketApp instance.
    mock_ws_instance = MagicMock()

    @patch('websocket.WebSocketApp')
    def test_play_clued_playable_card(self, mock_websocketapp):
        """When negative information is sufficient to tell us to play."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_stacks = [0, 0, 0, 0, 1]
        state.player_hands[0][1].clues = [Clue(hint_type=2, hint_value=3, classification=1)]
        client = get_default_client(state)

        client.decide_action()

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY.value, 'target': 1})


    @patch('websocket.WebSocketApp')
    def test_play_deduced_playable_card(self, mock_websocketapp):
        """When negative information is sufficient to tell us to play."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_stacks = [0, 1, 1, 1, 1]
        state.player_hands[0][0].negative_ranks = [2,3,4,5]
        state.player_hands[0][0].negative_colors = [1,2,3,4]
        client = get_default_client(state)

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY.value, 'target': 0})

    @patch('websocket.WebSocketApp')
    def test_discard_when_without_clue_tokens(self, mock_websocketapp):
        """When no clues is available (and no cards to play), discard."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.clue_tokens = 0
        client = get_default_client(state)

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.DISCARD.value, 'target': 0})

    @patch('websocket.WebSocketApp')
    def test_discard_trash(self, mock_websocketapp):
        """When no clues is available (and no cards to play), discard."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.clue_tokens = 0
        state.player_hands[0][1].rank = 5
        state.player_hands[0][1].suit_index = 3
        state.discard_pile = [Card(order=10, rank=4, suit_index=3), Card(order=10, rank=4, suit_index=3)]
        client = get_default_client(state)

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.DISCARD.value, 'target': 1})


    @patch('websocket.WebSocketApp')
    def test_discard_played_trash_card(self, mock_websocketapp):
        """When no clues is available (and no cards to play), discard."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.clue_tokens = 0
        state.play_stacks = [5, 5, 2, 3, 4]
        state.player_hands[0][2].rank = 2
        client = get_default_client(state)

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.DISCARD.value, 'target': 2})

    @patch('websocket.WebSocketApp')
    def test_give_clue(self, mock_websocketapp):
        """Give simple immediate clue."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.player_hands[1][3].rank = 1
        client = get_default_client(state)

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.COLOR_CLUE.value, 'target': 1, 'value': 1})

if __name__ == '__main__':
    unittest.main()
