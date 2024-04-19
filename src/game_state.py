"""The game snapshot of a moment."""
from dataclasses import dataclass, field

from src.card import Card
from src.constants import MAX_CLUE_NUM, MAX_RANK, MAX_CARDS_PER_RANK


# This is just a reference. For a fully-fledged bot, the game state would need
# to be more specific. (For example, a card object should contain the positive
# and negative clues that are "on" the card.)
# pylint: disable=too-few-public-methods
@dataclass
class GameState:
    """The game state from our own view."""

    replaying_past_actions: bool = True
    clue_tokens: int = MAX_CLUE_NUM
    player_names: list = field(default_factory=list)
    our_player_index: int = -1

    # Cards in different players' hands (i.e., 2D array of Card objects).
    player_hands: list = field(default_factory=list)

    # An array of suits' rank (i.e., 1D array).
    play_stacks: list = field(default_factory=list)
    discard_pile: list = field(default_factory=list)

    turn: int = -1
    current_player_index: int = -1

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
        # Untouched card is usually useful.
        if card.suit_index == -1 and card.rank == -1:
            return False

        if card.suit_index == -1 and card.rank != -1:
            # If all suits are equal or above the rank, then it is a trash.
            for i in range(5):
                if self.play_stacks[i] < card.rank:
                    return False
            return True

        if card.suit_index != -1 and card.rank == -1:
            # It is a trash if this color is completed, or, the next rank are discarded.
            if self.play_stacks[card.suit_index] == 5:
                return True
            count = 0
            next_rank = 1 + self.play_stacks[card.suit_index]
            for discard in self.discard_pile:
                if discard.suit_index == card.suit_index and discard.rank == next_rank:
                    count += 1
            return count == MAX_CARDS_PER_RANK[next_rank]

        # Is this card already played?
        if self.play_stacks[card.suit_index] >= card.rank:
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
            if num_discarded == MAX_CARDS_PER_RANK[i]:
                return True
        return False

    def is_critical(self, card: Card):
        if self.is_trash(card):
            return False

        if card.rank == 5:
            return True

        if card.rank == 1:
            return False

        for discarded_card in self.discard_pile:
            if discarded_card.rank == card.rank and discarded_card.suit_index == card.suit_index:
                return True
        return False

    def is_playable(self, card: Card):
        if self.is_trash(card):
            return False

        if card.suit_index != -1 and card.rank != -1:
            return self.play_stacks[card.suit_index] + 1 == card.rank

        # incomplete information
        clues = card.clues
        if len(clues) == 0:
            # No clue at all, then check finesse info.
            return (card.finesse_color != -1
            and card.finesse_rank != -1
            and self.play_stacks[card.finesse_color] + 1 == card.finesse_rank)

        # With clue(s), then check the latest clue whether play or not.
        return clues[-1].classification == 1
