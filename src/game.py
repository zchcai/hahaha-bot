"""The table of a game with our player index."""

import copy
import random

from dataclasses import dataclass, field

from src.action import Action
from src.card import Card
from src.clue import Clue
from src.constants import (
    ACTION,
    MAX_BOOM_NUM,
    MAX_CARDS_PER_PLAYER,
    MAX_CARDS_PER_RANK,
    MAX_CLUE_NUM,
    MAX_RANK,
)
from src.snapshot import Snapshot
from src.utils import printf, dump


# This is just a reference. For a fully-fledged bot, the game state would need
# to be more specific. (For example, a card object should contain the positive
# and negative clues that are "on" the card.)
# pylint: disable=too-few-public-methods
@dataclass
class Game:
    """The game from our view."""

    """Ground truth information."""
    clue_tokens: int = MAX_CLUE_NUM
    boom_tokens: int = MAX_BOOM_NUM
    num_suits: int = 5  # default as no variant

    player_names: list = field(default_factory=list)

    # An array of played cards (i.e., 1D array of Card objects).
    play_pile: list = field(default_factory=list)
    # An array of discarded cards (i.e., 1D array of Card objects).
    # It also contains the boomed cards.
    discard_pile: list = field(default_factory=list)

    """Mutually shared information."""
    # A map between card order (unique No.) to its colors or/and ranks.
    # When private views get conflict with mutually shared information, private views must be wrong.
    clued_colors: dict = field(default_factory=dict)
    clued_ranks: dict = field(default_factory=dict)

    """Mixed information."""
    # Cards in different players' hands (i.e., 2D array of Card objects).
    # For "our_player_index", it means "what we think" of our hand.
    # For other players, it means "what we think they think" of their hands.
    player_hands: list = field(default_factory=list)

    # The index of the player who is us.
    our_player_index: int = -1

    # An array of game snapshot history from our view (i.e., 1D array of Snapshot objects).
    snapshot_history: list = field(default_factory=list)

    # An array of original action (i.e., 1D array of Action objects).
    # It also contains drawing actions.
    action_history: list = field(default_factory=list)

    def take_initial_snapshot(self):
        s = Snapshot()
        s.initialize(len(self.player_names), 0, self.player_hands)
        self.snapshot_history.append(s)

    def handle_action(self, action: Action):
        # Pre-action intention check.

        # Record the action.
        if action.action_type == ACTION.DRAW.value:
            # Draw action in the beginning is not recorded.
            self.handle_draw(action)
        elif action.action_type == ACTION.PLAY.value:
            if action.boom:
                self.handle_boom(action)
            else:
                self.handle_play(action)
        elif action.action_type == ACTION.DISCARD.value:
            self.handle_discard(action)
        elif (
            action.action_type == ACTION.COLOR_CLUE.value
            or action.action_type == ACTION.RANK_CLUE.value
        ):
            self.handle_clue(action)

        if len(self.snapshot_history) > 0 and action.action_type != ACTION.DRAW.value:
            self.snapshot_history.append(
                self.snapshot_history[-1].next_snapshot(action)
            )

    def pre_action_intention_check(
        self, viewer_index: int = None, player_index: int = None
    ) -> list:
        # default as our player
        if viewer_index is None:
            viewer_index = self.our_player_index
        # default as the current player
        if player_index is None:
            player_index = self.current_player_index()
        if (
            viewer_index != self.our_player_index
            or player_index != self.our_player_index
        ):
            # TODO: analyze other players' intention from a specified view
            return []

        # Check whether we need to save the discard slot of the next player.

        # Any play at our hand?

        # Any clue at our hand?

        # The server expects to be told about actions in the following format:
        # https://github.com/Hanabi-Live/hanabi-live/blob/main/server/src/command_action.go

        cards = self.player_hands[player_index]
        num_cards = len(cards)

        """
        Action forced situation:
        1. Bluff position and they are possibly be bluffed.
        2. Next player will boom or discard a critical card if nothing special happens.
        """

        # Decide what to do.
        # TODO: correct any immediately required private views. For example, this includes:
        # 1. bluff reaction (i.e., false finesse annotation)
        # 2. Critical card save (i.e., useful signal or save clues)

        # Check if any players' discard slot needs to be saved.
        for player in range(len(self.player_hands)):
            if player == self.our_player_index:
                continue
            discard_slot = self.current_discard_slot(player)
            if discard_slot is not None and self.is_critical(discard_slot):
                if self.will_not_discard(player):
                    continue

                # We need to save them!
                # TODO: we don't need to save them if:
                # - they have playable cards to clue or
                # - they have cards to play now.
                if self.clue_tokens > 0:
                    return [
                        Action(
                            action_type=ACTION.RANK_CLUE.value,
                            player_index=self.our_player_index,
                            clue=Clue(
                                hint_type=ACTION.RANK_CLUE.value,
                                hint_value=discard_slot.rank,
                                giver_index=self.our_player_index,
                                receiver_index=player,
                            ),
                        )
                    ]
                # Be creative!
                my_discard_slot = self.current_discard_slot(self.our_player_index)
                if my_discard_slot is not None:
                    return [
                        Action(
                            action_type=ACTION.DISCARD.value,
                            card=my_discard_slot,
                            player_index=self.our_player_index,
                        )
                    ]
                return [
                    Action(
                        action_type=ACTION.PLAY.value,
                        card=cards[-1],
                        player_index=self.our_player_index,
                    )
                ]

        # Play cards if possible.
        for i in range(num_cards):
            # From draw slot to discard slot
            card = cards[num_cards - i - 1]
            if self.is_playable(card):
                return [
                    Action(
                        action_type=ACTION.PLAY.value,
                        card=card,
                        player_index=self.our_player_index,
                    )
                ]

        # Discard when neither a play nor a clue.
        if self.clue_tokens <= 0:
            self.clue_tokens = 0
            return [self.try_discard(cards)]

        # TODO: don't clue already clued cards.
        # Try to clue immediate playable cards by color clue or rank clue.
        # First, search all playable candidates.
        immediate_playable_cards_per_player = []
        for player in range(len(self.player_names)):
            immediate_playable_cards_per_player.append([])
            if player == self.our_player_index:
                continue
            for card in self.player_hands[player]:
                if self.is_playable(card):
                    immediate_playable_cards_per_player[player].append(card)
            if len(immediate_playable_cards_per_player[player]) == 0:
                # no immediate playable card for this player
                continue

            # Second, check each candidate one by one.
            for playable_card in immediate_playable_cards_per_player[player]:
                target_color = playable_card.suit_index
                target_rank = playable_card.rank

                # Is it already been clued or not?
                if len(playable_card.clues) > 0:
                    # Is it given a play clue?
                    if playable_card.clues[-1].classification == 1:
                        continue
                    # Otherwise, we just double clue it with different clue.
                    if playable_card.clues[-1].hint_type == ACTION.RANK_CLUE.value:
                        return [
                            Action(
                                action_type=ACTION.COLOR_CLUE.value,
                                player_index=self.our_player_index,
                                clue=Clue(
                                    hint_type=ACTION.COLOR_CLUE.value,
                                    hint_value=target_color,
                                    giver_index=self.our_player_index,
                                    receiver_index=player,
                                ),
                            )
                        ]
                    return [
                        Action(
                            action_type=ACTION.RANK_CLUE.value,
                            player_index=self.our_player_index,
                            clue=Clue(
                                hint_type=ACTION.RANK_CLUE.value,
                                hint_value=target_rank,
                                giver_index=self.our_player_index,
                                receiver_index=player,
                            ),
                        )
                    ]

                # Can we give color clue or rank clue?
                can_give_color_clue = True
                can_give_rank_clue = True
                # First check whether there is any card left to it.
                for i in range(num_cards):
                    potential_touched_card = self.player_hands[player][i]
                    if potential_touched_card.suit_index == target_color:
                        # if the order is larger, it means it is left to it.
                        if potential_touched_card.order > playable_card.order:
                            can_give_color_clue = False
                    if potential_touched_card.rank == target_rank:
                        if potential_touched_card.order > playable_card.order:
                            can_give_rank_clue = False

                # For playable cards, color clue is better than rank clue.
                if can_give_color_clue:
                    return [
                        Action(
                            action_type=ACTION.COLOR_CLUE.value,
                            player_index=self.our_player_index,
                            clue=Clue(
                                hint_type=ACTION.COLOR_CLUE.value,
                                hint_value=target_color,
                                giver_index=self.our_player_index,
                                receiver_index=player,
                            ),
                        )
                    ]
                if can_give_rank_clue:
                    return [
                        Action(
                            action_type=ACTION.RANK_CLUE.value,
                            player_index=self.our_player_index,
                            clue=Clue(
                                hint_type=ACTION.RANK_CLUE.value,
                                hint_value=target_rank,
                                giver_index=self.our_player_index,
                                receiver_index=player,
                            ),
                        )
                    ]

        # Nothing we can do, so discard.
        return [self.try_discard(cards)]

    def post_action_evaluation(self, intented_actions: list):
        pass

    # --------------------------------------
    # AI logic or functions from this point.
    #
    # Every convention needs 2 main parts to implement: giving and receiving clues.
    #
    # For each turn, there will be execution-evaluation loops:
    # 1. Action predication based on mutually shared information and private views.
    # 2a. Other people's turn: Compare the real action and predicated one.
    # 2b. Our own turn: Compare the outcome and our assumption.
    # --------------------------------------

    def handle_draw(self, action: Action):
        # self.snapshot_history[-1].hands[action.player_index].append(action.card)
        self.player_hands[action.player_index].append(action.card)
        self.action_history.append(action)
        if (
            len(self.action_history)
            == len(self.player_names) * MAX_CARDS_PER_PLAYER[len(self.player_names)]
        ):
            # All players have drawn their cards.
            # Now we need to decide our action.
            self.take_initial_snapshot()

    def handle_play(self, action: Action):
        # TODO: pre-/post- analysis.

        # Extract the copy from the player's hand after removal.
        card = self.remove_card_from_hand(action.player_index, action.card.order)
        # Record the real value of this card.
        card.rank = action.card.rank
        card.suit_index = action.card.suit_index
        self.play_pile.append(card)
        # Record this action in history with the updated card information.
        action.card = card
        self.action_history.append(action)

    def handle_discard(self, action: Action):
        # TODO: pre-/post- analysis.

        # Extract the copy from the player's hand after removal.
        card = self.remove_card_from_hand(action.player_index, action.card.order)
        # Record the real value of this card.
        card.rank = action.card.rank
        card.suit_index = action.card.suit_index
        self.discard_pile.append(card)
        # Record this action in history with the updated card information.
        action.card = card
        self.clue_tokens += 1
        self.action_history.append(action)

    def handle_boom(self, action: Action):
        # TODO: pre-/post- analysis.

        # Extract the copy from the player's hand after removal.
        card = self.remove_card_from_hand(action.player_index, action.card.order)
        # Record the real value of this card.
        card.rank = action.card.rank
        card.suit_index = action.card.suit_index
        self.discard_pile.append(card)
        # Record this action in history with the updated card information.
        action.card = card
        self.boom_tokens -= 1
        self.action_history.append(action)

    def handle_clue(self, action: Action):
        # Add clue into touched cards.
        clue = action.clue
        cards = self.player_hands[clue.receiver_index]

        # Exception: special handling for 1s.
        if clue.hint_type == ACTION.RANK_CLUE.value and clue.hint_value == 1:
            # All 1s are marked as playable firstly.
            # If this is a trash clue, it will be corrected by calculating
            # the potential slot.
            # TODO: trash bluff is not implemented.
            clue.classification = 1
            for card in cards:
                if card.order in clue.touched_orders:
                    card.add_clue(clue)
                else:
                    card.add_negative_info(clue)

            # Update game state: each clue costs one clue token.
            self.clue_tokens -= 1
            self.action_history.append(action)
            return

        # Double clued cards will be analyzed several times.
        double_clued_cards = self.double_clued_cards(clue.receiver_index, clue)

        # First, we need to see whether this is a Save Clue by checking
        # whether touching the discard slot.
        discard_slot = self.current_discard_slot(clue.receiver_index)

        if (
            discard_slot is not None
            and discard_slot.order in clue.touched_orders
            and clue.hint_type == ACTION.RANK_CLUE.value
        ):
            # The discard slot is touched by a rank clue!
            # It is possible to be a Save Clue depends on whether clue-receiver has playable cards.
            possible_save_mark = True
            possible_save_suit = []

            # Is it a non-5 critical save?
            if clue.hint_value != 5:
                possible_save_mark = False
                for discarded_card in self.critical_non_5_cards():
                    if discarded_card.rank == clue.hint_value:
                        # This is a critical save.
                        possible_save_mark = True
                        possible_save_suit.append(discarded_card.suit_index)

            # Now we know the touched discard slot is possible a save and its possible suits.
            # However, maybe this is caused by a double-touch Play Clue.
            if possible_save_mark:
                # Check whether any double touched card is **newly** playable.
                # If so, then we treat this as a Play Clue and mark all playable cards.
                play_clue_added_card_orders = []
                if len(double_clued_cards) > 0:
                    for possible_playable_card in double_clued_cards:
                        pending_focused_card = copy.deepcopy(possible_playable_card)
                        pending_focused_card.add_clue(clue)
                        if (
                            not self.is_playable(possible_playable_card)
                        ) and self.is_playable(pending_focused_card):
                            clue.classification = 1
                            possible_playable_card.add_clue(clue)
                            play_clue_added_card_orders.append(
                                possible_playable_card.order
                            )

                    if len(play_clue_added_card_orders) > 0:
                        # Some cards are marked now. It is a double-touch Play Clue.
                        # For all other cards, assign save mark.
                        clue.classification = 2
                        for card in cards:
                            if card.order not in clue.touched_orders:
                                card.add_negative_info(clue)
                            else:
                                if card.order not in play_clue_added_card_orders:
                                    card.add_clue(clue)
                        # Update game state: each clue costs one clue token.
                        self.clue_tokens -= 1
                        self.action_history.append(action)
                        return

                # Otherwise, this is a Save Clue.
                # All cards are marked as save and try to deduce the suit.
                clue.classification = 2
                for card in cards:
                    if card.order in clue.touched_orders:
                        card.add_clue(clue)
                    else:
                        card.add_negative_info(clue)

                if len(possible_save_suit) > 0:
                    for i in range(5):
                        if i not in possible_save_suit:
                            discard_slot.add_negative_suit(i)

                # Update game state: each clue costs one clue token.
                self.clue_tokens -= 1
                self.action_history.append(action)
                return

        # It is a Play Clue now.
        # The focus is default as the left-most touched card, however, we should check
        # double-touched card firstly.
        play_focus_card_order = []

        # Exception: double clued newly playable cards.
        if len(double_clued_cards) > 0:
            # Check whether any double touched card is **newly** playable.
            # If so, then we adjust our focus to them, instead of the left-most touched card.
            for possible_playable_card in double_clued_cards:
                pending_focused_card = copy.deepcopy(possible_playable_card)
                pending_focused_card.add_clue(clue)
                if (not self.is_playable(possible_playable_card)) and self.is_playable(
                    pending_focused_card
                ):
                    clue.classification = 1
                    possible_playable_card.add_clue(clue)
                    play_focus_card_order.append(possible_playable_card.order)

        # No newly playable card, and thus we mark the left-most touched card as the focus.
        # TODO: need more tests on edge cases.
        if len(play_focus_card_order) == 0:
            play_focus_card_order.append(max(clue.touched_orders))

        for card in cards:
            if card.order in clue.touched_orders:
                if card.order in play_focus_card_order:
                    clue.classification = 1
                else:
                    clue.classification = 2
                card.add_clue(clue)
            else:  # append negative information
                card.add_negative_info(clue)

        # Update game state: each clue costs one clue token.
        self.clue_tokens -= 1
        self.action_history.append(action)
        return

    def decide_action(self):
        s = Snapshot()
        s.play_pile = self.play_pile
        s.discard_pile = self.discard_pile
        s.hands = self.player_hands
        s.clue_tokens = self.clue_tokens
        s.boom_tokens = self.boom_tokens
        s.num_suits = self.num_suits
        s.num_players = len(self.player_names)

        game_valid_actions = s.get_valid_actions(
            self.our_player_index, self.our_player_index
        )
        dump(game_valid_actions)
        # return game_valid_actions[random.randint(0, len(game_valid_actions) - 1)]
        return self.pre_action_intention_check(
            self.our_player_index, self.our_player_index
        )[0]

    def try_discard(self, cards):
        if self.clue_tokens == MAX_CLUE_NUM:
            # The idea is to give highly possible trash 1s or save 5s.
            for i in [1, 5, 2, 3, 4]:
                for j, hand in enumerate(self.player_hands):
                    if j == self.our_player_index:
                        continue
                    for card in hand:
                        if card.rank == i:
                            return Action(
                                action_type=ACTION.RANK_CLUE.value,
                                player_index=self.our_player_index,
                                clue=Clue(
                                    hint_type=ACTION.RANK_CLUE.value,
                                    hint_value=i,
                                    giver_index=self.our_player_index,
                                    receiver_index=j,
                                ),
                            )

        # Discard trash cards firstly.
        for card in cards:
            if self.is_trash(card):
                return Action(
                    action_type=ACTION.DISCARD.value,
                    card=card,
                    player_index=self.our_player_index,
                )

        # Then oldest unclued card.
        for card in cards:
            if len(card.clues) == 0:
                return Action(
                    action_type=ACTION.DISCARD.value,
                    card=card,
                    player_index=self.our_player_index,
                )
        return Action(
            action_type=ACTION.PLAY.value,
            card=cards[-1],
            player_index=self.our_player_index,
        )

    def current_player_index(self):
        turns = 0
        for action in self.action_history:
            if action.action_type != ACTION.DRAW.value:
                turns += 1
        return turns % len(self.player_names)

    def critical_non_5_cards(self):
        """Returns cards that are critical to save but not 5."""
        critical_cards = []
        if len(self.discard_pile) == 0:
            return critical_cards

        for discarded_card in self.discard_pile:
            # Check each discarded card whether critical to save.
            rank = discarded_card.rank
            suit = discarded_card.suit_index

            if rank == 5:
                # only care about non-5 cards
                continue

            if self.play_stacks()[suit] >= rank:
                # already played
                continue

            # Firstly, check whether the other cards are also discarded.
            if self.count_discarded(rank, suit) >= MAX_CARDS_PER_RANK[suit][rank]:
                continue

            # Second, check whether this card can be played later.
            can_be_played_later = True
            for pending_rank in range(self.play_stacks()[suit] + 1, rank):
                if (
                    self.count_discarded(pending_rank, suit)
                    >= MAX_CARDS_PER_RANK[suit][pending_rank]
                ):
                    # This card cannot be played later.
                    can_be_played_later = False

            if not can_be_played_later:
                continue

            # Finally, whether this card is already seen in other players' hand.
            if self.seen_in_hands(rank, suit):
                continue

            critical_cards.append(discarded_card)

        return critical_cards

    def seen_in_hands(self, rank, suit):
        """Check whether this card is seen in other players' hand."""
        for hand in self.player_hands:
            for card in hand:
                if card.rank == rank and card.suit_index == suit:
                    return True
        return False

    def count_discarded(self, rank, suit):
        """Count the number of cards discarded with the given rank and suit."""
        count = 0
        for card in self.discard_pile:
            if card.rank == rank and card.suit_index == suit:
                count += 1
        return count

    def will_not_discard(self, player):
        for card in self.player_hands[player]:
            for clue in card.clues:
                if clue.classification == 1:
                    return True
        return False

    def double_clued_cards(self, player, clue):
        double_clued = []
        for card in self.player_hands[player]:
            if card.order in clue.touched_orders and len(card.clues) > 0:
                # There is a double clued card now.
                double_clued.append(card)
        return double_clued

    def current_discard_slot(self, player):
        for card in self.player_hands[player]:
            if len(card.clues) == 0:
                return card
        return None

    def is_trash(self, card: Card):
        # Untouched card is usually assumed as useful.
        if card.suit_index == -1 and card.rank == -1:
            return False

        # Hinted or deduced to know the number.
        if card.suit_index == -1 and card.rank != -1:
            # If all possible suits are equal or above the rank, then it is a trash.
            for i in range(5):
                if i in card.negative_colors:
                    # skip impossible color
                    continue
                if self.play_stacks()[i] < card.rank:
                    return False
            return True

        # Hinted or deduced to know the color.
        if card.suit_index != -1 and card.rank == -1:
            # It is a trash if this color is completed.
            if self.play_stacks()[card.suit_index] == MAX_RANK:
                return True

            # It is a trash if the next number is discarded already.
            count = 0
            next_rank = 1 + self.play_stacks()[card.suit_index]
            for discard in self.discard_pile:
                if discard.suit_index == card.suit_index and discard.rank == next_rank:
                    count += 1
            if count == MAX_CARDS_PER_RANK[card.suit_index][next_rank]:
                return True

            # It is a trash if it cannot be the remaining number(s).
            # Either seen from the discard slot, or from other hands.
            for j in range(next_rank, MAX_RANK + 1):
                if j in card.negative_ranks:
                    # skip impossible rank
                    continue

                # check whether this number is all visible.
                count = 0
                for hand in self.player_hands:
                    for c in hand:
                        if c.rank == j and c.suit_index == card.suit_index:
                            count += 1
                for discard in self.discard_pile:
                    if discard.suit_index == card.suit_index and discard.rank == j:
                        count += 1
                if count < MAX_CARDS_PER_RANK[card.suit_index][j]:
                    # It is still useful.
                    return False
            # all possible remaining ranks are impossible.
            return True

        # Is this card already played?
        if self.play_stacks()[card.suit_index] >= card.rank:
            return True
        # If no cards have been discarded, it is not a trash.
        if len(self.discard_pile) == 0:
            return False
        # Is this card's previous rank not available?
        for i in range(1, card.rank):
            num_discarded = 0
            for discard in self.discard_pile:
                if discard.suit_index == card.suit_index and discard.rank == i:
                    num_discarded += 1
            if num_discarded == MAX_CARDS_PER_RANK[card.suit_index][i]:
                return True
        return False

    def remove_card_from_hand(self, player_index, order):
        hand = self.player_hands[player_index]

        card_index = -1
        for i, card in enumerate(hand):
            if card.order == order:
                card_index = i
                break

        if card_index == -1:
            printf(
                "error: unable to find card with order " + str(order) + " in"
                "the hand of player " + str(player_index)
            )
            return None

        card = copy.deepcopy(hand[card_index])
        del hand[card_index]
        return card

    def is_critical(self, card: Card):
        if self.is_trash(card):
            return False

        if card.rank == 5:
            return True

        if card.rank == 1:
            return False

        for discarded_card in self.discard_pile:
            if (
                discarded_card.rank == card.rank
                and discarded_card.suit_index == card.suit_index
            ):
                return True
        return False

    def play_stacks(self):
        stacks = [0] * self.num_suits
        for card in self.play_pile:
            stacks[card.suit_index] = max(card.rank, stacks[card.suit_index])
        return stacks

    # TODO: good touch principle
    def is_playable(self, card: Card):
        if self.is_trash(card):
            return False

        if card.suit_index != -1 and card.rank != -1:
            return self.play_stacks()[card.suit_index] + 1 == card.rank

        # incomplete information
        clues = card.clues
        finesses = card.finesses
        if len(clues) == 0:
            # No clue at all, then check finesse info.
            if len(finesses) == 0:
                # No finesse paths touched either, then not playable.
                return False
            else:
                # TODO: finesse handling.
                # Now if it is not empty, then it is playable.
                return True

        # Firstly check the latest clue whether play or not.
        # If it never becomes a focus, don't play.
        with_play_clue = False
        for clue in clues:
            if clue.classification == 1:
                with_play_clue = True
        if with_play_clue is False:
            return False

        # Secondly, even interpreted as Play Clue(s), it is possible a save.
        if card.rank != -1:
            # no color information.
            # check whether it is a save.
            for suit in range(5):
                if card.rank == self.play_stacks()[suit] + 1:
                    # If the last clue is not play, then don't play it now.
                    return False if clues[-1].classification == 2 else True
            # not possible to be playable.
            return False

        return True
