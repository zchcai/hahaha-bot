"""Client constants, matching the server side:
https://github.com/Hanabi-Live/hanabi-live/blob/master/server/src/constants.go
"""

from dataclasses import dataclass


@dataclass
class ACTION:
    """ Valid player actions in Hanabi.
    https://github.com/Hanabi-Live/hanabi-live/blob/c936808df2b78aa4a24be7b0d622fceb75393f17/server/src/constants.go#L23
    """
    PLAY = 0
    DISCARD = 1
    COLOR_CLUE = 2
    RANK_CLUE = 3


# The maximum amount of clues (and the amount of clues that players start the
# game with).
# https://github.com/Hanabi-Live/hanabi-live/blob/c936808df2b78aa4a24be7b0d622fceb75393f17/server/src/constants.go#L91
MAX_CLUE_NUM = 8
