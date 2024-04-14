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

    # probability graph

    def __init__(self, order, rank, suit_index):
        self.order = order
        self.rank = rank
        self.suit_index = suit_index
        self.clues = []

    def add_clue(self, clue: Clue):
        self.clues.append(copy.deepcopy(clue))
