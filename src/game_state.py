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

            if self.play_stacks[suit] >= rank:
                # already played
                continue

            # Firstly, check whether the other cards are also discarded.
            if self.count_discarded(rank, suit) >= MAX_CARDS_PER_RANK[rank]:
                continue

            # Second, check whether this card can be played later.
            can_be_played_later = True
            for pending_rank in range(self.play_stacks[suit] + 1, rank):
                if self.count_discarded(pending_rank, suit) >= MAX_CARDS_PER_RANK[pending_rank]:
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
                if self.play_stacks[i] < card.rank:
                    return False
            return True

        # Hinted or deduced to know the color.
        if card.suit_index != -1 and card.rank == -1:
            # It is a trash if this color is completed.
            if self.play_stacks[card.suit_index] == MAX_RANK:
                return True

            # It is a trash if the next number is discarded already.
            count = 0
            next_rank = 1 + self.play_stacks[card.suit_index]
            for discard in self.discard_pile:
                if discard.suit_index == card.suit_index and discard.rank == next_rank:
                    count += 1
            if count == MAX_CARDS_PER_RANK[next_rank]:
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
                if count < MAX_CARDS_PER_RANK[j]:
                    # It is still useful.
                    return False
            # all possible remaining ranks are impossible.
            return True

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

    # TODO: good touch principle
    def is_playable(self, card: Card):
        if self.is_trash(card):
            return False

        if card.suit_index != -1 and card.rank != -1:
            return self.play_stacks[card.suit_index] + 1 == card.rank

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
                if card.rank == self.play_stacks[suit] + 1:
                    # If the last clue is not play, then don't play it now.
                    return False if clues[-1].classification == 2 else True
            # not possible to be playable.
            return False

        return True
