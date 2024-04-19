"""The metadata for one clue."""

from dataclasses import dataclass, field

# pylint: disable=too-few-public-methods

@dataclass
class Clue:
    """The basic information for a clue."""

    # basic information
    hint_type: int = -1     # 1 - rank, 2 - color
    hint_value: int = -1    # suit_index (color) or rank

    # players infomation
    giver_index: int = -1
    receiver_index: int = -1

    # game information
    turn: int = -1

    # classification of this clue
    classification: int = -1 # 1 - "play", 2 - "save", 3 - "trash"

    # touched cards orders (i.e., No.)
    touched_orders: list = field(default_factory=list)
