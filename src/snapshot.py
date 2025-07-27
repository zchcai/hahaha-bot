"""The game snapshot of a moment."""

import copy

from dataclasses import dataclass, field
from typing import Optional

from src.card import Card
from src.clue import Clue
from src.action import Action
from src.constants import (
    ACTION,
    Color,
    MAX_BOOM_NUM,
    MAX_CLUE_NUM,
    MAX_RANK,
    MAX_CARDS_PER_RANK,
    Status,
)
from src.finesse import Finesse
from src.utils import dump, printf


# This is just a reference. For a fully-fledged bot, the game state would need
# to be more specific. (For example, a card object should contain the positive
# and negative clues that are "on" the card.)
# pylint: disable=too-few-public-methods
@dataclass
class Snapshot:
    """Table information."""

    clue_tokens: int = MAX_CLUE_NUM
    boom_tokens: int = MAX_BOOM_NUM
    num_suits: int = 5  # default as no variant
    num_remaining_cards: int = -1
    post_draw_turns: int = 0
    num_players: int = -1
    start_player_index: int = -1

    # An array of played cards (i.e., 1D array of Card objects).
    play_pile: list = field(default_factory=list)
    # An array of discarded cards (i.e., 1D array of Card objects).
    # It also contains the boomed cards.
    discard_pile: list = field(default_factory=list)

    """Mixed information."""
    # Cards in different players' hands (i.e., 2D array of Card objects).
    # For "player_index", it means "what we think" of our hand.
    # For other players, it means "what we think they think" of their hands.
    hands: list = field(default_factory=list)

    """Transition information."""
    # An array of initial cards (i.e., 1D array of Card objects).
    initial_cards: list = field(default_factory=list)
    # An array of original action (i.e., 1D array of Action objects).
    action_history: list = field(default_factory=list)

    def initialize(self, num_players, start_player_index, hands):
        self.num_players = num_players
        self.start_player_index = start_player_index
        self.hands = hands
        self.num_remaining_cards = sum(
            sum(MAX_CARDS_PER_RANK[i]) for i in range(self.num_suits)
        )
        for hand in hands:
            for card in hand:
                self.num_remaining_cards -= 1
                self.initial_cards.append(card)

    def next_snapshot(self, action: Action, viewer_index=None):
        """Return the next snapshot after taking the action.
        The action is assumed to be game-valid.
        """
        next_snapshot = Snapshot(
            clue_tokens=self.clue_tokens,
            boom_tokens=self.boom_tokens,
            num_suits=self.num_suits,
            num_players=self.num_players,
            play_pile=copy.deepcopy(self.play_pile),
            discard_pile=copy.deepcopy(self.discard_pile),
            hands=[copy.deepcopy(hand) for hand in self.hands],
            initial_cards=copy.deepcopy(self.initial_cards),
            action_history=copy.deepcopy(self.action_history),
        )
        next_snapshot._perform_action(action, viewer_index)
        next_snapshot.action_history.append(action)
        return next_snapshot

    def get_valid_actions(self, viewer_index: int, player_index: int) -> list:
        """Get all game-valid actions for a player from a viewer's view.
        Game-valid means it is doable by the game rules, even if it means a boom.
        """
        actions = []
        if self.is_end_status():
            # Game is over, no more actions allowed.
            return actions

        # Playing a card is always valid.
        for card in self.hands[player_index]:
            actions.append(
                Action(
                    action_type=ACTION.PLAY.value,
                    player_index=player_index,
                    card=Card(card.order),
                )
            )

        # Discarding a card is valid except clue tokens are full.
        if self.clue_tokens < MAX_CLUE_NUM:
            for card in self.hands[player_index]:
                actions.append(
                    Action(
                        action_type=ACTION.DISCARD.value,
                        player_index=player_index,
                        card=Card(card.order),
                    )
                )

        # Without any clue tokens, no more clues can be given.
        if self.clue_tokens <= 0:
            return actions

        # All possible clues towards other players' hand are valid.
        for i in range(self.num_players):
            cards = self.hands[i]
            if i == player_index:
                # A player cannot clue themselves.
                continue
            if i == viewer_index:
                # It is theoretically possible to clue the viewer from the player, however,
                # from the viewer's perspective, it is unexpected.
                continue
            valid_ranks = []
            valid_suits = []
            for card in cards:
                if card.rank != -1 and card.rank not in valid_ranks:
                    valid_ranks.append(card.rank)
                if card.suit_index != -1 and card.suit_index not in valid_suits:
                    valid_suits.append(card.suit_index)
            for rank in valid_ranks:
                actions.append(
                    Action(
                        action_type=ACTION.RANK_CLUE.value,
                        player_index=player_index,
                        clue=Clue(
                            hint_type=ACTION.RANK_CLUE.value,
                            giver_index=player_index,
                            receiver_index=i,
                            hint_value=rank,
                            touched_orders=[
                                _c.order for _c in cards if _c.rank == rank
                            ],
                        ),
                    )
                )
            for suit in valid_suits:
                actions.append(
                    Action(
                        action_type=ACTION.COLOR_CLUE.value,
                        player_index=player_index,
                        clue=Clue(
                            hint_type=ACTION.COLOR_CLUE.value,
                            giver_index=player_index,
                            receiver_index=i,
                            hint_value=suit,
                            touched_orders=[
                                _c.order for _c in cards if _c.suit_index == suit
                            ],
                        ),
                    )
                )
        return actions

    def is_end_status(self) -> bool:
        # Boom tokens are used up.
        if self.boom_tokens <= 0:
            return True
        # All possible cards are played.
        if len(self.play_pile) == self._max_score_limit():
            return True
        # All cards are drawn and everyone finishes the final turn.
        if self.num_remaining_cards == 0 and self.post_draw_turns == self.num_players:
            return True
        return False

    def _max_score_limit(self) -> int:
        theoretical_max_score = self.num_suits * MAX_RANK
        if len(self.discard_pile) == 0:
            return theoretical_max_score

        discard_ranks = self.discard_table()
        for suit in range(self.num_suits):
            for rank in range(1, MAX_RANK + 1):
                if discard_ranks[suit][rank] == MAX_CARDS_PER_RANK[suit][rank]:
                    theoretical_max_score -= MAX_RANK - rank + 1
                    break
        return theoretical_max_score

    def _perform_action(self, action: Action, viewer_index=None):
        if action.action_type == ACTION.DRAW.value:
            self._perform_draw(action, viewer_index)
            return

        if action.action_type == ACTION.PLAY.value:
            if action.boom:
                self._perform_boom(action, viewer_index)
            else:
                self._perform_play(action, viewer_index)
        elif action.action_type == ACTION.DISCARD.value:
            self._perform_discard(action, viewer_index)
        elif action.action_type in (ACTION.COLOR_CLUE.value, ACTION.RANK_CLUE.value):
            self._perform_clue(action, viewer_index)

        if self.num_remaining_cards == 0:
            self.post_draw_turns += 1

    def _perform_draw(self, action: Action, viewer_index=None):
        self.hands[action.player_index].append(action.card)
        self.num_remaining_cards -= 1
        if viewer_index is None:
            viewer_index = action.player_index

        # Based on the draw, rule out relevant possibility in everyone's notes.

    def _perform_play(self, action: Action, viewer_index=None):
        self.play_pile.append(
            self._remove_card_from_hand(action.player_index, action.card.order)
        )
        if viewer_index is None:
            viewer_index = action.player_index

        # The (immediate) next player(s) will update information depends on situations.
        # Depends on available know playable cards.
        # Depends on playing a clued or unclued card.

    def _perform_discard(self, action: Action, viewer_index=None):
        if viewer_index is None:
            viewer_index = action.player_index

        discarded_card = self.get_card_from_hand(action.player_index, action.card.order)

        if discarded_card.status not in [
            Status.TRASH_KNOWN_BY_PLAYER,
            Status.UNSPECIFIED,
        ]:
            # Re-position.
            raise Exception(
                "Discarded card is possibly useful. It might mean re-positioning."
            )

        # The immediate next player will update information depends on situations.
        # Depends on clues amount: 2+, 1, or 0:
        # Depends on whether there is a known playable card.
        # Depends on discard n-th supposed card.
        next_player_index = (action.player_index + 1) % self.num_players
        known_playable_cards = False
        for c in self.hands[action.player_index]:
            if c.status == Status.PLAYABLE_KNOWN_BY_PLAYER:
                known_playable_cards = True
        cards_pending_discard_with_order = []
        # The iteration order starts from the discard slot to draw slot.
        for c in self.hands[action.player_index]:
            if c.status == Status.TRASH_KNOWN_BY_PLAYER:
                cards_pending_discard_with_order.append(c.order)
        for c in self.hands[action.player_index]:
            if (
                c.order not in cards_pending_discard_with_order
                and c.status == Status.UNSPECIFIED
            ):
                cards_pending_discard_with_order.append(c.order)

        num_cards_to_save = 0
        if discarded_card.order not in cards_pending_discard_with_order:
            # This should not happen.
            # Otherwise, very special case.
            raise Exception("Discarded card is not expected at all.")

        discarded_card_index = -1
        for index, order_index in enumerate(cards_pending_discard_with_order):
            if discarded_card.order == order_index:
                discarded_card_index = index
                break

        if discarded_card_index == 0:
            if known_playable_cards is True:
                # Now, this player should not discard. Also, not saveable by clues.
                # It must at least save one card,
                # either for the next turn, or planning for the future.
                num_cards_to_save = (1 if self.clue_tokens > 0 else 0) + 1
        else:
            # Count how many cards to save for the next player.

            # no immediately playable cards:
            # 1. No clues (0), offset 1 discard: 1
            # 2. No clues (0), offset 2 discard: 2
            # 3. 1+ clue, offset 1 discard: 2
            # 4. 1+ clue, offset 2 discard: 3

            # own immediately playable cards:
            # 1. No clues (0), offset 1 discard: 2
            # 2. No clues (0), offset 2 discard: 3
            # 3. 1+ clue, offset 1 discard: 3
            # 4. 1+ clue, offset 2 discard: 4
            num_cards_to_save = (
                self.clue_tokens
                + discarded_card_index
                + (1 if known_playable_cards is True else 0)
            )

        # Conditionally mark the next player's untouched or unclued cards as saved.
        if num_cards_to_save > 0:
            marked = 0
            for card in self.hands[next_player_index]:
                if card.status not in [
                    Status.CLUED_SAVED,
                    Status.DIRECT_FINESSED,
                    Status.GOOD_TOUCH_SAVED,
                    Status.INDIRECT_FINESSED,
                    Status.PLAYABLE_KNOWN_BY_PLAYER,
                ]:
                    card.status = Status.USEFUL
                    marked += 1
                    if marked == num_cards_to_save:
                        break

        # DO_NOT_MODIFY_BEGIN
        self.discard_pile.append(
            self._remove_card_from_hand(action.player_index, action.card.order)
        )
        self.clue_tokens += 1
        # DO_NOT_MODIFY_END

    def _perform_boom(self, action: Action, viewer_index=None):
        self.discard_pile.append(
            self._remove_card_from_hand(action.player_index, action.card.order)
        )
        self.boom_tokens -= 1
        if viewer_index is None:
            viewer_index = action.player_index

    def _perform_clue(self, action: Action, viewer_index=None):
        # DO_NOT_MODIFY_BEGIN
        self.clue_tokens -= 1
        # DO_NOT_MODIFY_END

        clue = action.clue
        receiver_cards = self.hands[clue.receiver_index]
        clued_cards = [  # from draw slot to discard slot
            self.get_card_from_hand(clue.receiver_index, _order)
            for _order in sorted(clue.touched_orders, reverse=True)
        ]
        double_clued_cards = self._double_clued_cards(clue)
        hinted_table = self.hints_table()
        if viewer_index is None:
            viewer_index = clue.receiver_index

        # Handle Rank Clue 1.
        if clue.hint_type == ACTION.RANK_CLUE.value and clue.hint_value == 1:
            # Check how many 1s left to clue.
            num_left_1s = self.num_suits
            # Remove played 1s.
            for rank_per_suit in self.played_ranks():
                if rank_per_suit >= 1:
                    num_left_1s -= 1
            # Remove clued 1s.
            for suit_index in range(self.num_suits):
                if hinted_table[suit_index][1] > 0:
                    num_left_1s -= 1
            # From draw slot to discard slot, mark playable notes.
            if num_left_1s < 1:
                # TODO: handle trash clue: (1) no useful 1s to clue (2) the leftmost is a trash 1
                # And the discard slot is useful.
                for card_1 in clued_cards:
                    card_1.status = Status.TRASH_KNOWN_BY_PLAYER
                return
            tagged = 0
            for _ in range(min(num_left_1s, len(clued_cards))):
                clued_cards[tagged].status = Status.PLAYABLE_KNOWN_BY_PLAYER
                tagged += 1
            if tagged < len(clued_cards):
                clued_cards[tagged].status = Status.TRASH_KNOWN_BY_PLAYER

        # Handle Non-Black Color Clue. (Play Clue)
        if clue.hint_type == ACTION.COLOR_CLUE.value and clue.hint_value != 5:
            # Check remaining possible ranks within this suit.
            possibility = [True] * (MAX_RANK + 1)
            possibility[0] = False
            # Remove played ranks.
            for rank in range(1, self.played_ranks()[clue.hint_value] + 1):
                possibility[rank] = False
            # Remove touched cards.
            for rank in range(1, MAX_RANK + 1):
                if hinted_table[clue.hint_value][rank] > 0:
                    possibility[rank] = False

            next_missing_rank = 6
            for i in range(1, MAX_RANK):
                if possibility[i]:
                    next_missing_rank = i
                    break
            if next_missing_rank > 5:
                # Trash clue.
                for card in clued_cards:
                    card.status = Status.TRASH_KNOWN_BY_PLAYER
            else:
                for i, card in enumerate(clued_cards):
                    if i == 0:
                        card.status = Status.DIRECT_FINESSED
                        card.add_finesse(
                            finesse=Finesse(
                                rank=next_missing_rank,
                                suit=clue.hint_value,
                            )
                        )
                    else:
                        card.status = Status.GOOD_TOUCH_SAVED

        # Handle Number Clue 2-5
        if (
            clue.hint_type == ACTION.RANK_CLUE.value
            and clue.hint_value > 1
            and clue.hint_value < 6
        ):
            # First, we need to see whether this is a Save Clue by checking
            # whether touching the pending discarding card.
            discard_slot = self._pending_discard_slot(clue.receiver_index, viewer_index)
            if (
                discard_slot is not None
                and discard_slot.order in clue.touched_orders
                and len(self._unique_suits_in_rank(clue.hint_value)) > 0
            ):
                discard_slot.status = Status.CLUED_SAVED

            else:
                # This is a Play Clue.
                possible_suits = [True] * self.num_suits
                # Remove played suits.
                for suit, rank in enumerate(self.played_ranks()):
                    if rank >= clue.hint_value:
                        possible_suits[suit] = False
                # Remove touched suits.
                for suit in range(self.num_suits):
                    if hinted_table[suit][clue.hint_value] > 0:
                        possible_suits[suit] = False
                for i, card in enumerate(clued_cards):
                    if i != 0:
                        card.status = Status.GOOD_TOUCH_SAVED
                        continue

                    card.status = Status.DIRECT_FINESSED
                    for suit, ok in enumerate(possible_suits):
                        if ok is False:
                            continue
                        card.add_finesse(
                            Finesse(
                                rank=clue.hint_value,
                                suit=suit,
                                # TODO: Determine potential actionable paths.
                            )
                        )
        # Handle black color.
        if (
            clue.hint_type == ACTION.COLOR_CLUE.value
            and clue.hint_value == Color.BLACK.value
        ):
            pass

    def _unique_suits_in_rank(self, rank: int):
        # First list all potential suits from the discarded pile.
        # Then remove them by clued or seen or played or good touch induced.
        discard_table = self.discard_table()
        played_ranks = self.played_ranks()
        ret = []
        for suit_index in range(self.num_suits):
            if (
                discard_table[suit_index][rank]
                == MAX_CARDS_PER_RANK[suit_index][rank] - 1
                and played_ranks[suit_index] < rank
            ):
                ret.append(suit_index)
        return ret

    def _pending_discard_slot(
        self, player_index: int, viewer_index: int = None
    ) -> Optional[Card]:
        cards = self.hands[player_index]
        if viewer_index is None:
            viewer_index = player_index
        # TODO: we need to predict the possibility in their turn, not the current snapshot.
        for card in cards:
            if card.status in [
                Status.PLAYABLE_KNOWN_BY_PLAYER,
                Status.TRASH_KNOWN_BY_PLAYER,
            ]:
                # This player won't plan to discard.
                return None
        # Then, first locate the first untouched or hinted card from right.
        for card in cards:
            if card.status == Status.UNSPECIFIED:
                return card
        # If no, then return the unclued one.
        for card in cards:
            if card.status in Status.USEFUL:
                return card

    def _double_clued_cards(self, clue):
        double_clued = []
        for card in self.hands[clue.receiver_index]:
            if card.order in clue.touched_orders and len(card.clues) > 0:
                # There is a double clued card now.
                double_clued.append(card)
        return double_clued

    def _remove_card_from_hand(self, player_index, order):
        card_index = self._get_card_slot_from_hand(
            player_index=player_index, order=order
        )
        if card_index == None:
            return None

        hand = self.hands[player_index]
        card = copy.deepcopy(hand[card_index])
        del hand[card_index]
        return card

    def _get_card_slot_from_hand(self, player_index, order):
        for i, card in enumerate(self.hands[player_index]):
            if card.order == order:
                return i
        printf(
            "error: unable to find card with order " + str(order) + " in "
            "the hand of player " + str(player_index)
        )
        return None

    def get_card_from_hand(self, player_index, order) -> Optional[Card]:
        """Get a card from a player's hand based on card order No."""
        card_index = self._get_card_slot_from_hand(
            player_index=player_index, order=order
        )
        if card_index == None:
            return None
        return self.hands[player_index][card_index]

    def hints_table(self, viewer_index=None):
        """Conclude current hints table, where it means which card is clued or not."""
        hints_table = [[0] * (MAX_RANK + 1) for _ in range(self.num_suits)]
        for player_index, player_hands in enumerate(self.hands):
            for card in player_hands:
                if card.status == Status.UNSPECIFIED:
                    continue
                if player_index == viewer_index:
                    # The truth of the card is not revealed.
                    continue
                if card.suit_index != -1 and card.rank != -1:
                    hints_table[card.suit_index][card.rank] += 1
                else:
                    # TODO: This card is not revealed from our player.
                    continue
        return hints_table

    def discard_table(self):
        """The current discarded cards."""
        discard_table = [[0] * (MAX_RANK + 1) for _ in range(self.num_suits)]
        for card in self.discard_pile:
            discard_table[card.suit_index][card.rank] += 1
        return discard_table

    def played_ranks(self):
        """The current discarded cards."""
        played = [0] * (self.num_suits)
        for card in self.play_pile:
            played[card.suit_index] = max(card.rank, played[card.suit_index])
        return played

    def recalculate_trash_cards(self, player_index: int, viewer_index: int = None):
        """Recalculate trash cards from public information (played, discarded, seen) and private
        views (clued, touched, saved).

        This function directly modifies card status for all players from viewer's perspective.
        """
        if viewer_index is None:
            viewer_index = player_index
        played_ranks = self.played_ranks()
        discard_table = self.discard_table()
        hinted_table = self.hints_table()
        for person_index in range(self.num_players):
            for card in self.hands[person_index]:
                if card.status == Status.TRASH_KNOWN_BY_PLAYER:
                    # Terminal state: a trash card cannot become a useful card any more.
                    continue
                if self.is_useful(card) is False:
                    card.status = Status.TRASH_KNOWN_BY_PLAYER
                    continue

    def is_useful(self, card: Card):
        played_ranks = self.played_ranks()
        if card.status == Status.TRASH_KNOWN_BY_PLAYER:
            return False
        # A finished rank.
        if card.rank != -1 and card.rank <= min(played_ranks):
            return False
        # A finished color.
        if (
            card.suit_index != Color.UNSPECIFIED.value
            and played_ranks[card.suit_index] == MAX_RANK
        ):
            return False
        # A unreachable card.
        discard_ranks = self.discard_table()
        if card.rank != -1 and card.suit_index != Color.UNSPECIFIED.value:
            for lower_rank in range(1, card.rank):
                if (
                    discard_ranks[card.suit_index][lower_rank]
                    == MAX_CARDS_PER_RANK[card.suit_index][lower_rank]
                ):
                    return False
        return True
