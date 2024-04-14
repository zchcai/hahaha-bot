"""The game snapshot of a moment."""

from src.card import Card
from src.constants import MAX_CLUE_NUM


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
        clues = card.clues
        if len(clues) == 0:
            return (card.finesse_color != -1
            and card.finesse_rank != -1
            and self.play_stacks[card.finesse_color] + 1 == card.finesse_rank)
        if clues[-1].classification == 1:
            return True
        return (card.suit_index != -1
        and card.rank != -1
        and self.play_stacks[card.suit_index] + 1 == card.rank)
