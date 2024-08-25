"""The metadata for one card."""

import copy

from dataclasses import dataclass, field
from src.clue import Clue
from src.constants import MAX_RANK
from src.finesse import Finesse

@dataclass
class Card:
    """Card information at one player's hand."""
    # basic information
    order: int = -1
    rank: int = -1
    suit_index: int = -1
    owner_index: int = -1

    # status
    # 0 - nothing/unclued/untouched
    # 1 - implicit unclued saved (useful, i.e., garbage clue at another card)
    # 2 - good touch saved (touched, useful, passive save)
    # 3 - explicit saved (touched, active save)
    # 4 - unclued finessed (untouched, actionable)
    # 5 - clued finessed (touched, actionable)
    # 6 - playable (immediately actionable)
    # (more status)
    # -1 - trash/useless
    status: int = 0

    # clues sequence
    clues: list = field(default_factory=list)

    # possible finesses sequence
    finesses: list = field(default_factory=list)

    # negative information
    negative_colors: list = field(default_factory=list)
    negative_ranks: list = field(default_factory=list)

    def add_finesse(self, finesse: Finesse):
        self.finesses.append(copy.copy(finesse))

    def add_clue(self, clue: Clue):
        self.clues.append(copy.copy(clue))
        if clue.hint_type == 1:
            self.rank = clue.hint_value
        elif clue.hint_type == 2:
            self.suit_index = clue.hint_value

        # TODO: fineese info

    def add_negative_suit(self, suit_index: int):
        """Add negative suit information."""
        if suit_index not in self.negative_colors:
            self.negative_colors.append(suit_index)

        # reflect negative information if possible
        if self.suit_index == -1 and len(self.negative_colors) == 5 - 1:
            for i in range(5):
                if i not in self.negative_colors:
                    self.suit_index = i
                    break

    def add_negative_rank(self, rank: int):
        """Add negative rank information."""
        if rank not in self.negative_ranks:
            self.negative_ranks.append(rank)

        # reflect negative information if possible
        if self.rank == -1 and len(self.negative_ranks) == MAX_RANK - 1:
            for i in range(1, MAX_RANK + 1):
                if i not in self.negative_ranks:
                    self.rank = i
                    break

    def add_negative_info(self, untouched_clue: Clue):
        """"Add negative information from a untouched clue."""
        if untouched_clue.hint_type == 1:
            self.add_negative_rank(untouched_clue.hint_value)
        elif untouched_clue.hint_type == 2:
            self.add_negative_suit(untouched_clue.hint_value)
