import unittest

# Imports (local application)
from src.action import Action
from src.card import Card
from src.clue import Clue
from src.constants import ACTION, Color, MAX_RANK, Status
from src.snapshot import Snapshot

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
                Card(order=4, rank=2, suit_index=Color.GREEN.value),  # discard slot
                Card(order=5, rank=3, suit_index=Color.PURPLE.value),
                Card(order=6, rank=2, suit_index=Color.GREEN.value),
                Card(order=7, rank=1, suit_index=Color.BLUE.value),  # draw slot
            ],
            [
                # Player 2
                Card(order=8, rank=1, suit_index=Color.RED.value),  # discard slot
                Card(order=9, rank=1, suit_index=Color.RED.value),
                Card(order=10, rank=2, suit_index=Color.RED.value),
                Card(order=11, rank=4, suit_index=Color.PURPLE.value),  # draw slot
            ],
            [
                # Player 3
                Card(order=12, rank=1, suit_index=Color.GREEN.value),  # discard slot
                Card(order=13, rank=2, suit_index=Color.BLUE.value),
                Card(order=14, rank=1, suit_index=Color.YELLOW.value),
                Card(order=15, rank=3, suit_index=Color.RED.value),  # draw slot
            ],
        ],
    )
    return snapshot


# Test class.
class TestSnapshot(unittest.TestCase):
    """Class to test helper functions in Snapshot."""

    def test_get_valid_actions(self):
        s = get_default_snapshot()

        actions = s.get_valid_actions(viewer_index=0, player_index=0)

        assert len(actions) == 22

    def test_get_valid_actions_no_clues(self):
        s = get_default_snapshot()
        s.clue_tokens = 0

        actions = s.get_valid_actions(viewer_index=0, player_index=0)

        assert len(actions) == 8

    def test_get_valid_actions_no_actions(self):
        s = get_default_snapshot()
        s.boom_tokens = 0

        actions = s.get_valid_actions(viewer_index=0, player_index=0)

        assert len(actions) == 0

    def test_get_valid_actions_predict_other_player(self):
        s = get_default_snapshot()
        s = s.next_snapshot(
            Action(
                action_type=ACTION.COLOR_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.COLOR_CLUE.value,
                    giver_index=0,
                    receiver_index=3,
                    hint_value=3,
                    touched_orders=[13],
                ),
            )
        )

        actions = s.get_valid_actions(viewer_index=0, player_index=1)

        assert len(actions) == 20

    def test_is_end_status(self):
        s = get_default_snapshot()

        assert not s.is_end_status()

    def test_is_end_status_boom_tokens_used_up(self):
        s = get_default_snapshot()
        s.boom_tokens = 0

        assert s.is_end_status()

    def test_is_end_status_all_cards_played(self):
        s = get_default_snapshot()

        for i in range(5):
            for j in range(1, 6):
                s.play_pile.append(Card(rank=j, suit_index=i))

        assert s.is_end_status()

    def test_is_end_status_all_possible_cards_played(self):
        s = get_default_snapshot()

        for i in range(4):
            for j in range(1, 6):
                s.play_pile.append(Card(rank=j, suit_index=i))
        s.play_pile.append(Card(rank=1, suit_index=4))
        s.discard_pile.append(Card(rank=2, suit_index=4))
        s.discard_pile.append(Card(rank=2, suit_index=4))
        s.discard_pile.append(Card(rank=3, suit_index=4))

        assert s.is_end_status()

    def test_is_end_status_cards_drawn(self):
        s = get_default_snapshot()
        s.num_remaining_cards = 0
        s.post_draw_turns = s.num_players

        assert s.is_end_status()

    def test_is_end_status_after_discard(self):
        s = get_default_snapshot()
        s.clue_tokens = 6
        for i in range(1, 5):
            for j in range(1, 6):
                s.play_pile.append(Card(rank=j, suit_index=i))
        s.play_pile.append(Card(rank=1, suit_index=0))
        s.discard_pile.append(Card(rank=2, suit_index=0))

        assert not s.is_end_status()  # 21/25

        s = s.next_snapshot(
            Action(
                action_type=ACTION.DISCARD.value,
                player_index=2,
                card=Card(order=10, rank=2, suit_index=0),
            )
        )

        assert s.is_end_status()  # 21/21

    def test_is_end_status_after_play(self):
        s = get_default_snapshot()
        for i in range(1, 5):
            for j in range(1, 6):
                s.play_pile.append(Card(rank=j, suit_index=i))
        s.play_pile.append(Card(rank=1, suit_index=0))
        s.play_pile.append(Card(rank=2, suit_index=0))
        s.discard_pile.append(Card(rank=4, suit_index=0))
        s.discard_pile.append(Card(rank=4, suit_index=0))

        assert not s.is_end_status()  # 22/23

        s = s.next_snapshot(
            Action(
                action_type=ACTION.PLAY.value,
                player_index=3,
                card=Card(order=15, rank=3, suit_index=0),
            )
        )

        assert s.is_end_status()  # 23/23

    def test_is_end_status_after_boom(self):
        s = get_default_snapshot()
        for i in range(1, 5):
            for j in range(1, 6):
                s.play_pile.append(Card(rank=j, suit_index=i))
        s.play_pile.append(Card(rank=1, suit_index=0))
        s.discard_pile.append(Card(rank=4, suit_index=0))
        s.discard_pile.append(Card(rank=4, suit_index=0))
        s.discard_pile.append(Card(rank=3, suit_index=0))

        assert not s.is_end_status()  # 21/23

        s = s.next_snapshot(
            Action(
                action_type=ACTION.PLAY.value,
                boom=True,
                player_index=3,
                card=Card(order=15, rank=3, suit_index=0),  # boom, 21/22
            )
        )
        assert not s.is_end_status()  # 21/23

        s = s.next_snapshot(
            Action(
                action_type=ACTION.PLAY.value,
                player_index=2,
                card=Card(order=10, rank=2, suit_index=0),
            )
        )
        assert s.is_end_status()  # 22/22

    def test_perform_clue_1s(self):
        s = get_default_snapshot()

        s = s.next_snapshot(
            Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=1,
                    giver_index=0,
                    receiver_index=3,
                    touched_orders=[14, 12],
                ),
            )
        )

        assert s.get_card_from_hand(3, 14).status == Status.PLAYABLE_KNOWN_BY_PLAYER
        assert s.get_card_from_hand(3, 12).status == Status.PLAYABLE_KNOWN_BY_PLAYER

    def test_perform_clue_1s_only_leftmost_playable(self):
        s = get_default_snapshot()
        s.play_pile.append(Card(rank=1, suit_index=0))
        s.play_pile.append(Card(rank=1, suit_index=2))
        s.play_pile.append(Card(rank=1, suit_index=3))
        s.play_pile.append(Card(rank=1, suit_index=4))

        s = s.next_snapshot(
            Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=1,
                    giver_index=0,
                    receiver_index=3,
                    touched_orders=[14, 12],
                ),
            )
        )

        assert s.get_card_from_hand(3, 14).status == Status.PLAYABLE_KNOWN_BY_PLAYER
        assert s.get_card_from_hand(3, 12).status == Status.TRASH_KNOWN_BY_PLAYER

    def test_perform_clue_1s_good_touch(self):
        s = get_default_snapshot()
        s.play_pile.append(Card(rank=1, suit_index=0))
        s.play_pile.append(Card(rank=1, suit_index=2))
        s.play_pile.append(Card(rank=1, suit_index=4))
        s.get_card_from_hand(1, 7).status = Status.PLAYABLE_KNOWN_BY_PLAYER

        s = s.next_snapshot(
            Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=1,
                    giver_index=0,
                    receiver_index=3,
                    touched_orders=[14, 12],
                ),
            )
        )

        assert s.get_card_from_hand(3, 14).status == Status.PLAYABLE_KNOWN_BY_PLAYER
        assert s.get_card_from_hand(3, 12).status == Status.TRASH_KNOWN_BY_PLAYER

    def test_perform_clue_1s_trash_clue(self):
        s = get_default_snapshot()
        for i in range(MAX_RANK):
            s.play_pile.append(Card(rank=1, suit_index=i))

        s = s.next_snapshot(
            Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=1,
                    giver_index=0,
                    receiver_index=3,
                    touched_orders=[14, 12],
                ),
            )
        )

        assert s.get_card_from_hand(3, 14).status == Status.TRASH_KNOWN_BY_PLAYER
        assert s.get_card_from_hand(3, 12).status == Status.TRASH_KNOWN_BY_PLAYER

    def test_perform_clue_color(self):
        s = get_default_snapshot()

        s = s.next_snapshot(
            action=Action(
                action_type=ACTION.COLOR_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.COLOR_CLUE.value,
                    hint_value=2,
                    giver_index=0,
                    receiver_index=3,
                    touched_orders=[12],
                ),
            ),
            viewer_index=3,
        )

        touched_card = s.get_card_from_hand(3, 12)
        assert touched_card.status == Status.DIRECT_FINESSED
        assert touched_card.finesses[0].rank == 1
        assert touched_card.finesses[0].suit == 2

    def test_perform_clue_color_trash(self):
        s = get_default_snapshot()
        for i in range(1, MAX_RANK + 1):
            s.play_pile.append(Card(rank=i, suit_index=0))

        s = s.next_snapshot(
            action=Action(
                action_type=ACTION.COLOR_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.COLOR_CLUE.value,
                    hint_value=0,
                    giver_index=0,
                    receiver_index=3,
                    touched_orders=[15],
                ),
            ),
            viewer_index=3,
        )

        touched_card = s.get_card_from_hand(3, 15)
        assert touched_card.status == Status.TRASH_KNOWN_BY_PLAYER

    def test_perform_clue_color_next_missing_rank(self):
        s = get_default_snapshot()
        s.hands[2][1].status = Status.PLAYABLE_KNOWN_BY_PLAYER
        s.hands[2][2].status = Status.PLAYABLE_KNOWN_BY_PLAYER

        s = s.next_snapshot(
            action=Action(
                action_type=ACTION.COLOR_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.COLOR_CLUE.value,
                    hint_value=0,
                    giver_index=0,
                    receiver_index=3,
                    touched_orders=[15],
                ),
            ),
            viewer_index=3,
        )

        touched_card = s.get_card_from_hand(3, 15)
        assert touched_card.status == Status.DIRECT_FINESSED
        assert touched_card.finesses[0].rank == 3
        assert touched_card.finesses[0].suit == 0

    def test_perform_clue_rank_save_5(self):
        s = get_default_snapshot()
        s.hands[1][0].rank = 5  # next player discard slot needs a save
        s.play_pile.append(Card(rank=1, suit_index=Color.BLUE.value))
        s.play_pile.append(Card(rank=1, suit_index=Color.YELLOW.value))
        # One card can be clued later, unfortnately, player 3's green 1 hasn't be clued yet.
        # Thus, we'd better first make the save for player 1.
        s = s.next_snapshot(
            action=Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=5,
                    giver_index=0,
                    receiver_index=1,
                    touched_orders=[4],
                ),
            ),
            viewer_index=1,
        )
        touched_card = s.get_card_from_hand(1, 4)
        assert touched_card.status == Status.CLUED_SAVED

    def test_perform_clue_rank_save_4(self):
        s = get_default_snapshot()
        s.hands[1][0].rank = 4  # next player discard slot needs a save
        s.play_pile.append(Card(rank=1, suit_index=Color.BLUE.value))
        s.play_pile.append(Card(rank=1, suit_index=Color.YELLOW.value))
        s.discard_pile.append(Card(rank=4, suit_index=Color.GREEN.value))
        # One card can be clued later, unfortnately, player 3's green 1 hasn't be clued yet.
        # Thus, we'd better first make the save for player 1.
        s = s.next_snapshot(
            action=Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=4,
                    giver_index=0,
                    receiver_index=1,
                    touched_orders=[4],
                ),
            ),
            viewer_index=1,
        )
        touched_card = s.get_card_from_hand(1, 4)
        assert touched_card.status == Status.CLUED_SAVED

    def test_perform_clue_rank_play_when_touching_discard(self):
        s = get_default_snapshot()
        s.hands[3][1].status = Status.DIRECT_FINESSED
        s.clue_tokens -= 1
        s.play_pile.append(Card(rank=1, suit_index=Color.BLUE.value))
        s.hands[1][1].suit_index = Color.BLUE.value
        s.hands[1][0].rank = 3

        # discard pile is empty and thus it must be a play clue.

        s = s.next_snapshot(
            action=Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=3,
                    giver_index=2,
                    receiver_index=1,
                    touched_orders=[4, 5],
                ),
            ),
            viewer_index=1,
        )
        assert s.get_card_from_hand(1, 4).status == Status.GOOD_TOUCH_SAVED
        assert s.get_card_from_hand(1, 5).status == Status.DIRECT_FINESSED
        # In this case, from player 1's view, it can be any color because they have 2 cards in front
        # of that 3. Later, they will wait and see whether player 3 play blue 2 over other cards.
        assert len(s.get_card_from_hand(1, 5).finesses) == s.num_suits

    def test_perform_clue_rank_play(self):
        s = get_default_snapshot()
        s.hands[3][1].status = Status.DIRECT_FINESSED
        s.clue_tokens -= 1
        s.play_pile.append(Card(rank=1, suit_index=Color.BLUE.value))
        s.hands[1][1].suit_index = Color.BLUE.value
        for suit in range(1, s.num_suits - 1):  # Red and Purple hasn't played yet.
            for rank in range(1, MAX_RANK + 1):
                s.play_pile.append(Card(rank=rank, suit_index=suit))
        s.hands[3][3].status = Status.DIRECT_FINESSED  # Red 3 is clued.

        s = s.next_snapshot(
            action=Action(
                action_type=ACTION.RANK_CLUE.value,
                player_index=0,
                clue=Clue(
                    hint_type=ACTION.RANK_CLUE.value,
                    hint_value=3,
                    giver_index=2,
                    receiver_index=1,
                    touched_orders=[5],
                ),
            ),
            viewer_index=1,
        )
        clued_card = s.get_card_from_hand(1, 5)
        assert clued_card.status == Status.DIRECT_FINESSED
        finesses = clued_card.finesses
        assert len(finesses) == 1
        assert finesses[0].suit == Color.PURPLE.value


if __name__ == "__main__":
    unittest.main()
