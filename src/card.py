"""The metadata for one card."""

import copy

from dataclasses import dataclass, field
from src.clue import Clue
from src.constants import MAX_RANK

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
        if clue.hint_type == 1:
            self.rank = clue.hint_value
        elif clue.hint_type == 2:
            self.suit_index = clue.hint_value

        # TODO: fineese info

    def add_negative_info(self, clue: Clue):
        if clue.hint_type == 1:
            if clue.hint_value not in self.negative_ranks:
                self.negative_ranks.append(clue.hint_value)
        elif clue.hint_type == 2:
            if clue.hint_value not in self.negative_colors:
                self.negative_colors.append(clue.hint_value)

        # reflect negative information if possible
        if self.suit_index == -1 and len(self.negative_colors) == 4:
            for i in range(5):
                if i not in self.negative_colors:
                    self.suit_index = i
                    break
        if self.rank == -1 and len(self.negative_ranks) == MAX_RANK - 1:
            for i in range(1, MAX_RANK + 1):
                if i not in self.negative_ranks:
                    self.rank = i
                    break
