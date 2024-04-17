"""The metadata for one card."""

import copy

from src.clue import Clue

class Card:
    """Card information at one player's hand."""

    # basic information
    order = -1
    rank = -1
    suit_index = -1

    # clue sequence
    clues: list[Clue] = []

    # finesse
    finesse_color = -1
    finesse_rank = -1

    # negative information
    negative_ranks: list[int] = []
    negative_colors: list[int] = []

    def __init__(self, order, rank=-1, suit_index=-1, clues=None, negative_ranks=None, negative_colors=None):
        self.order = order
        self.rank = rank
        self.suit_index = suit_index
        if clues is not None:
            self.clues = copy.deepcopy(clues)
        if negative_ranks is not None:
            self.negative_ranks = copy.deepcopy(negative_ranks)
        if negative_colors is not None:
            self.negative_colors = copy.deepcopy(negative_colors)


    def add_clue(self, clue: Clue):
        self.clues.append(copy.deepcopy(clue))
