"""The metadata for one card."""

import copy

from dataclasses import dataclass, field
from src.clue import Clue

@dataclass
class Card:
    """Card information at one player's hand."""
    # basic information
    order: int = -1
    rank: int = -1
    suit_index: int = -1

    # clue sequence
    clues: list = field(default_factory=list)

    # finesse
    finesse_color: int = -1
    finesse_rank: int = -1

    # negative information
    negative_colors: list = field(default_factory=list)
    negative_ranks: list = field(default_factory=list)

    def add_clue(self, clue: Clue):
        self.clues.append(copy.copy(clue))
