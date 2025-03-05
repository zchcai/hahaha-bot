"""The game snapshot of a moment."""
from dataclasses import dataclass, field

from src.card import Card
from src.action import Action
from src.constants import MAX_BOOM_NUM, MAX_CLUE_NUM, MAX_RANK, MAX_CARDS_PER_RANK


# This is just a reference. For a fully-fledged bot, the game state would need
# to be more specific. (For example, a card object should contain the positive
# and negative clues that are "on" the card.)
# pylint: disable=too-few-public-methods
@dataclass
class Snapshot:
    """Table information."""
    clue_tokens: int = MAX_CLUE_NUM
    boom_tokens: int = MAX_BOOM_NUM
    num_suits: int = 5 # default as no variant
    num_players: int = -1
    start_player_index: int = -1

    # An array of played cards (i.e., 1D array of Card objects).
    play_pile: list = field(default_factory=list)
    # An array of discarded cards (i.e., 1D array of Card objects).
    # It also contains the boomed cards.
    discard_pile: list = field(default_factory=list)

    """Mixed information."""
    # Cards in different players' hands (i.e., 2D array of Card objects).
    # For "player_index", it means "what we think" of our hand.
    # For other players, it means "what we think they think" of their hands.
    hands: list = field(default_factory=list)

    """Transition information."""
    # An array of initial cards (i.e., 1D array of Card objects).
    initial_cards: list = field(default_factory=list)
    # An array of original action (i.e., 1D array of Action objects).
    action_history: list = field(default_factory=list)

    def __init__(self, num_players, start_player_index, hands):
        self.num_players = num_players
        self.start_player_index = start_player_index
        self.hands = hands
        for hand in hands:
            for card in hand:
                self.initial_cards.append(card)
    
    def next_snapshot(self, action: Action):
        """
        Return the next snapshot after taking the action.
        The action is assumed to be valid.
        """
        next_snapshot = Snapshot(
            clue_tokens=self.clue_tokens,
            boom_tokens=self.boom_tokens,
            num_suits=self.num_suits,
            num_players=self.num_players,
            play_pile=self.play_pile.copy(),
            discard_pile=self.discard_pile.copy(),
            hands=[hand.copy() for hand in self.hands],
            snapshot_history=self.snapshot_history.copy(),
            action_history=self.action_history.copy()
        )
        next_snapshot.perform_action(action)
        next_snapshot.action_history.append(action)
        return next_snapshot
    
    def perform_action(self, action: Action):
        if action.action_type == 1:
            self.perform_play(action)
        elif action.action_type == 2:
            self.perform_discard(action)
        elif action.action_type == 3:
            self.perform_clue(action)

    def perform_play(self, action: Action):
        card = action.card
        self.hands[action.player_index].remove(card)
        self.play_pile.append(card)
        if action.next_card is not None:
            self.hands[action.player_index].append(action.next_card)
    
    def perform_discard(self, action: Action):
        card = action.card
        self.hands[action.player_index].remove(card)
        self.discard_pile.append(card)
        if action.boom:
            self.boom_tokens -= 1
        else:
            self.clue_tokens += 1
        if action.next_card is not None:
            self.hands[action.player_index].append(action.next_card)
    
    def perform_clue(self, action: Action):
        self.clue_tokens -= 1

    def annotate(self, previous_snapshot):
        """
        Annotate the snapshot with the differences from the previous snapshot.
        """
        pass
    
# Higher-level functions that can be used to predict the next actions.
# These functions should be implemented in a separate file.
# It returns a list of actions that can be taken by the actor.
def predict_next_actions(snapshot, viewer_index, actor_index):
    """Predict the next actions on behalf of a pair of viewer and actor."""
    return []
