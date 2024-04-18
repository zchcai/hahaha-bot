"""Client constants, matching the server side:
https://github.com/Hanabi-Live/hanabi-live/blob/master/server/src/constants.go
"""

from enum import Enum, auto

class ACTION(Enum):
    """ Valid player actions in Hanabi.
    https://github.com/Hanabi-Live/hanabi-live/blob/c936808df2b78aa4a24be7b0d622fceb75393f17/server/src/constants.go#L23
    """
    PLAY = 0
    DISCARD = auto()
    COLOR_CLUE = auto()
    RANK_CLUE = auto()


# The maximum amount of clues (and the amount of clues that players start the
# game with).
# https://github.com/Hanabi-Live/hanabi-live/blob/c936808df2b78aa4a24be7b0d622fceb75393f17/server/src/constants.go#L91
MAX_CLUE_NUM = 8

# No matter which suits, the max rank is always 5.
MAX_RANK = 5

# TODO: enable multi-color version later
MAX_CARDS_PER_RANK = [0, 3, 2, 2, 2, 1]
