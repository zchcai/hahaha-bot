"""The metadata for one action."""

from dataclasses import dataclass

from src.card import Card
from src.clue import Clue


@dataclass
class Action:
    """The basic information for an action."""

    action_type: int = -1  # PLAY, DISCARD, COLOR_CLUE, RANK_CLUE, ..., DRAW
    player_index: int = -1
    # Required for play, discard and draw actions.
    card: Card = None
    # Required for clue actions, which contains receiver_index and all touched cards.
    clue: Clue = None

    """The final outcome of this action."""
    # Required for play action.
    boom: bool = False
