"""The basic structure of a finesse."""

from dataclasses import dataclass, field

@dataclass
class Finesse:
    """A finesse."""
    # unified information
    rank: int = -1
    suit: int = -1
    urgent: bool = False

    # Linked clues.
    clues: list = field(default_factory=list)

    # per actionable path (specific to number clue)
    actionable_paths: list = field(default_factory=list)

    # per player
    giver: int = -1
    receivers: list = field(default_factory=list)
