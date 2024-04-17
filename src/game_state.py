"""The game snapshot of a moment."""

from src.card import Card
from src.constants import MAX_CLUE_NUM, MAX_RANK


# This is just a reference. For a fully-fledged bot, the game state would need
# to be more specific. (For example, a card object should contain the positive
# and negative clues that are "on" the card.)
# pylint: disable=too-few-public-methods
class GameState:
    """The game state from our own view."""

    replaying_past_actions = True
    clue_tokens = MAX_CLUE_NUM
    player_names = []
    our_player_index: int = -1

    # Cards in different players' hands (i.e., 2D array of Card objects).
    player_hands = []

    # An array of suits' rank (i.e., 1D array).
    play_stacks = []
    discard_pile = []

    turn: int = -1
    current_player_index: int = -1

    def is_playable(self, card: Card):
        # reflect negative information if possible
        if card.suit_index == -1 and len(card.negative_colors) == 4:
            for i in range(5):
                if i not in card.negative_colors:
                    card.suit_index = i
                    break
        if card.rank == -1 and len(card.negative_ranks) == MAX_RANK - 1:
            for i in range(1, MAX_RANK + 1):
                if i not in card.negative_ranks:
                    card.rank = i
                    break
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
