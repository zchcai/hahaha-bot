"""The metadata for one action."""

from dataclasses import dataclass, field

from src.card import Card
from src.clue import Clue

@dataclass
class Action:
    """The basic information for an action."""
    action_type: int = -1  # ACTION.PLAY, ACTION.DISCARD, ACTION.COLOR_CLUE, ACTION.RANK_CLUE
    player_index: int = -1
    # Required for play and discard actions.
    card: Card = None
    # Required for clue action, which contains receiver_index and all touched cards.
    clue: Clue = None

    """The final outcome of this action."""
    # Required for play action.
    boom: bool = False

    """The immediate next card."""
    # Must be None for clue action.
    next_card: Card = None