"""Unit Tests for HanabiClient."""

import unittest

from unittest.mock import patch, MagicMock

# Imports (local application)
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.game import Game
from src.hanabi_client import HanabiClient
from src.utils import dump

# Fake helpful constants.
FAKE_TABLE_ID = 42

# Helper functions
def get_default_game_state():
    state = Game()
    state.current_player_index = 0
    state.our_player_index = 0
    state.clue_tokens = 8
    state.player_names = ['Alice', 'Bob']
    state.player_hands = [
        # Player 0 (self)
        [
            Card(order=0),  # discard slot
            Card(order=1),
            Card(order=2),
            Card(order=3),
            Card(order=4),  # draw slot
        ],
        # Player 1 (the next player)
        [
            Card(order=5, rank=4, suit_index=1),    # discard slot
            Card(order=6, rank=2, suit_index=3),
            Card(order=7, rank=3, suit_index=4),
            Card(order=8, rank=4, suit_index=1),
            Card(order=9, rank=4, suit_index=0),    # draw slot
        ]
    ]
    return state

def get_default_client(game_state: Game=None):
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
    def test_record_rank_clue_5s_at_discard_slot_as_save(self, mock_websocketapp):
        """When save clue is given."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_pile = [Card(rank=1, suit_index=1)]
        state.player_hands[0][0].add_clue(
            Clue(hint_type=ACTION.COLOR_CLUE.value, hint_value=1, giver_index=1, receiver_index=0, classification=2,
                 turn=0, touched_orders=[0, 4]))
        state.player_hands[0][4].order = 10
        state.current_player_index = 1
        client = get_default_client(state)

        data =  {
            'type': 'clue', 
            'clue': {'type': 1, 'value': 5}, 
            'giver': 1, 
            'list': [1], 
            'target': 0, 
            'turn': 2
        }
        client.handle_action(data, FAKE_TABLE_ID)

        dump(state.player_hands[0])
        assert state.player_hands[0][1].clues[0].classification == 2


    @patch('websocket.WebSocketApp')
    def test_record_rank_clue_3s_at_discard_slot_as_save(self, mock_websocketapp):
        """When save clue is given."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_pile = [
            Card(rank=1, suit_index=0),
            Card(rank=2, suit_index=0),
            Card(rank=1, suit_index=1),
            Card(rank=1, suit_index=2),
            Card(rank=2, suit_index=2),
        ]
        state.turn = 2
        state.player_hands[0][0].add_clue(
            Clue(hint_type=ACTION.COLOR_CLUE.value, hint_value=2, giver_index=1, receiver_index=0, classification=2,
                 turn=0, touched_orders=[0, 4]))
        state.player_hands[0][4].order = 10
        state.discard_pile.append(Card(rank=3, suit_index=3))
        state.current_player_index = 1
        client = get_default_client(state)

        data =  {
            'type': 'clue', 
            'clue': {'type': 1, 'value': 3},    # rank clue
            'giver': 1, 
            'list': [1], 
            'target': 0, 
            'turn': 2
        }
        client.handle_action(data, FAKE_TABLE_ID)

        dump(state.player_hands[0])
        assert state.player_hands[0][1].clues[0].classification == 2
        assert state.player_hands[0][1].rank == 3
        assert state.player_hands[0][1].suit_index == 3


    @patch('websocket.WebSocketApp')
    def test_record_rank_clue_1s_as_play(self, mock_websocketapp):
        """When play clue is given."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.current_player_index = 1
        client = get_default_client(state)

        data =  {'type': 'clue', 'clue': {'type': 1, 'value': 1}, 'giver': 1, 'list': [1, 3], 
                 'target': 0, 'turn': 0}
        client.handle_action(data, FAKE_TABLE_ID)

        assert state.player_hands[0][1].clues == [
            Clue(hint_type=ACTION.RANK_CLUE.value, hint_value=1, giver_index=1, receiver_index=0, classification=1, 
                 turn=0, touched_orders=[1, 3])]
        assert state.player_hands[0][3].clues == [
            Clue(hint_type=ACTION.RANK_CLUE.value, hint_value=1, giver_index=1, receiver_index=0, classification=1,
                 turn=0, touched_orders=[1, 3])]


    @patch('websocket.WebSocketApp')
    def test_record_double_clued_card(self, mock_websocketapp):
        """When play clue is given."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_pile = [Card(rank=1, suit_index=0),
            Card(rank=1, suit_index=1),
            Card(rank=2, suit_index=1),
            Card(rank=1, suit_index=2)]
        state.current_player_index = 1
        state.clue_tokens = 3
        state.turn = 10
        state.player_hands[0][0].add_clue(
            Clue(hint_type=2, hint_value=1, classification=2, touched_orders=[0]))
        state.player_hands[0][1].add_clue(
            Clue(hint_type=2, hint_value=0, classification=2, touched_orders=[1]))
        state.player_hands[0][2].add_clue(
            Clue(hint_type=2, hint_value=1, classification=2, touched_orders=[2]))
        state.player_hands[0][3].add_clue(
            Clue(hint_type=2, hint_value=0, classification=2, touched_orders=[3]))

        client = get_default_client(state)

        data =  {'type': 'clue', 'clue': {'type': 1, 'value': 3}, 'giver': 1, 'list': [1, 2],
                 'target': 0, 'turn': 10}
        client.handle_action(data, FAKE_TABLE_ID)

        assert state.is_playable(state.player_hands[0][2])
        assert state.player_hands[0][2].rank == 3
        assert state.player_hands[0][2].suit_index == 1
        assert state.player_hands[0][2].clues[-1].classification == 1
        assert state.player_hands[0][1].clues[-1].classification == 2

    @patch('websocket.WebSocketApp')
    def test_record_play_clue(self, mock_websocketapp):
        """When play clue is given."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_pile = [Card(rank=1, suit_index=4)]
        state.current_player_index = 1
        client = get_default_client(state)

        data =  {'type': 'clue', 'clue': {'type': ACTION.COLOR_CLUE.value, 'value': 1}, 'giver': 1, 'list': [0, 3], 
                 'target': 0, 'turn': 0}
        client.handle_action(data, FAKE_TABLE_ID)

        assert state.player_hands[0][3].clues == [
            Clue(hint_type=2, hint_value=1, giver_index=1, receiver_index=0, classification=1,
                 turn=0, touched_orders=[0, 3])]
        assert state.player_hands[0][0].clues == [
            Clue(hint_type=2, hint_value=1, giver_index=1, receiver_index=0, classification=2, 
                 turn=0, touched_orders=[0, 3])]


# Test class.
class TestDecideAction(unittest.TestCase):
    """Class to test decide_action() function."""
    # Setup: Create a MagicMock for the WebSocketApp instance.
    mock_ws_instance = MagicMock()

    @patch('websocket.WebSocketApp')
    def test_play_1s(self, mock_websocketapp):
        """Play 1s."""
        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.clue_tokens = 7
        state.turn = 1
        state.player_hands[0][1].rank = 1
        state.player_hands[0][1].clues = [
            Clue(hint_type=ACTION.RANK_CLUE.value, hint_value=1, giver_index=1, receiver_index=0, classification=1,
                 turn=0, touched_orders=[1])]
        client = get_default_client(state)

        client.decide_action()

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY.value, 'target': 1})

    @patch('websocket.WebSocketApp')
    def test_play_card_when_no_emergency_but_with_playable_card_to_clue(self, mock_websocketapp):
        """When play clue is given."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_pile = [
            Card(rank=1, suit_index=0),
            Card(rank=1, suit_index=1),
            Card(rank=2, suit_index=1),
            Card(rank=1, suit_index=2),
        ]
        state.current_player_index = 0
        state.clue_tokens = 3
        state.turn = 11
        state.player_hands[0][0].add_clue(
            Clue(hint_type=2, hint_value=1, classification=2, touched_orders=[0]))
        state.player_hands[0][1].add_clue(
            Clue(hint_type=2, hint_value=0, classification=2, touched_orders=[1]))
        state.player_hands[0][1].add_clue(
            Clue(hint_type=1, hint_value=3, classification=2, touched_orders=[1, 2]))
        state.player_hands[0][2].add_clue(
            Clue(hint_type=2, hint_value=1, classification=2, touched_orders=[2]))
        state.player_hands[0][2].add_clue(
            Clue(hint_type=1, hint_value=3, classification=1, touched_orders=[1, 2]))
        state.player_hands[0][3].add_clue(
            Clue(hint_type=2, hint_value=0, classification=2, touched_orders=[3]))

        state.player_hands[1][3].rank = 2
        state.player_hands[1][3].suit_index = 0

        client = get_default_client(state)

        client.decide_action()

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY.value, 'target': 2})

    @patch('websocket.WebSocketApp')
    def test_do_not_give_save_clue_when_player_is_busy(self, mock_websocketapp):
        """When the player has things to do, don't save them."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_piles = [Card(rank=1, suit_index=3), Card(rank=1, suit_index=4)]
        # Their discard slot needs to be saved.
        state.player_hands[1][0].rank = 5
        # They have a play.
        state.player_hands[1][1].clues = [Clue(hint_type=2, hint_value=3, classification=1)]
        # We also have a play.
        state.player_hands[0][1].clues = [Clue(hint_type=2, hint_value=4, classification=1)]
        client = get_default_client(state)

        client.decide_action()

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY.value, 'target': 1})

    @patch('websocket.WebSocketApp')
    def test_give_save_clue_when_player_is_not_busy(self, mock_websocketapp):
        """When the player has things to do, don't save them."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_pile = [Card(rank=1, suit_index=4), Card(rank=1, suit_index=3)]
        # Their discard slot needs to be saved.
        state.player_hands[1][0].rank = 5
        # We have a play.
        state.player_hands[0][1].clues = [Clue(hint_type=2, hint_value=4, classification=1)]
        client = get_default_client(state)

        client.decide_action()

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.RANK_CLUE.value, 'target':  1, "value": 5})

    @patch('websocket.WebSocketApp')
    def test_play_clued_playable_card(self, mock_websocketapp):
        """When negative information is sufficient to tell us to play."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.play_pile = [Card(rank=1, suit_index=4)]
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
        state.play_pile = [
            Card(rank=1, suit_index=1),
            Card(rank=1, suit_index=2),
            Card(rank=1, suit_index=3),
            Card(rank=2, suit_index=3),
            Card(rank=1, suit_index=4),
        ]
        for i in range(2, 6):
            state.player_hands[0][0].add_negative_info(Clue(hint_type=ACTION.RANK_CLUE.value, hint_value=i))
        for i in range(1, 5):
            state.player_hands[0][0].add_negative_info(Clue(hint_type=ACTION.COLOR_CLUE.value, hint_value=i))
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
        state.discard_pile = [Card(order=10, rank=4, suit_index=3),
                              Card(order=10, rank=4, suit_index=3)]
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
        # [5, 5, 2, 3, 4]
        state.play_pile = [
            Card(rank=1, suit_index=0),
            Card(rank=2, suit_index=0),
            Card(rank=3, suit_index=0),
            Card(rank=4, suit_index=0),
            Card(rank=5, suit_index=0),
            Card(rank=1, suit_index=1),
            Card(rank=2, suit_index=1),
            Card(rank=3, suit_index=1),
            Card(rank=4, suit_index=1),
            Card(rank=5, suit_index=1),
            Card(rank=1, suit_index=2),
            Card(rank=2, suit_index=2),
            Card(rank=1, suit_index=3),
            Card(rank=2, suit_index=3),
            Card(rank=3, suit_index=3),
            Card(rank=1, suit_index=4),
            Card(rank=2, suit_index=4),
            Card(rank=3, suit_index=4),
            Card(rank=4, suit_index=4),
        ]
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

    @patch('websocket.WebSocketApp')
    def test_play_when_no_emergency(self, mock_websocketapp):
        """Play when no emergency."""

        mock_websocketapp.return_value = self.mock_ws_instance
        state = get_default_game_state()
        state.current_player_index = 0
        state.our_player_index = 0
        state.clue_tokens = 1
        state.play_pile = [
            Card(rank=1, suit_index=0),
            Card(rank=2, suit_index=0),
            Card(rank=3, suit_index=0),
            Card(rank=4, suit_index=0),
            Card(rank=1, suit_index=1),
            Card(rank=2, suit_index=1),
            Card(rank=1, suit_index=4),
            Card(rank=2, suit_index=4),
            Card(rank=3, suit_index=4),
        ]
        state.player_names = ['Alice', 'Bob']
        state.player_hands = [
            # Player 0 (self)
            [
                Card(order=0, rank=5, suit_index=4, clues=[
                    Clue(hint_type=ACTION.RANK_CLUE.value, hint_value=5, classification=2, touched_orders=[0]),
                    Clue(hint_type=ACTION.COLOR_CLUE.value, hint_value=4, classification=2, touched_orders=[0, 3])]),  # discard slot
                Card(order=1),
                Card(order=2),
                Card(order=3, suit_index=4, clues=[
                    Clue(hint_type=ACTION.COLOR_CLUE.value, hint_value=4, classification=1, touched_orders=[0, 3])]),
                Card(order=4)   # draw slot
            ],
            # Player 1 (the next player)
            [
                Card(order=5, rank=4, suit_index=2),    # discard slot
                Card(order=6, rank=2, suit_index=1),
                Card(order=7, rank=5, suit_index=2),
                Card(order=8, rank=4, suit_index=2),
                Card(order=9, rank=2, suit_index=2),    # draw slot
            ]
        ]
        client = get_default_client(state)

        client.decide_action(FAKE_TABLE_ID)

        client.send.assert_called_once_with(
            'action',
            {'tableID': FAKE_TABLE_ID, 'type': ACTION.PLAY.value, 'target': 3}
        )

if __name__ == '__main__':
    unittest.main()
