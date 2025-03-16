"""The game snapshot of a moment."""
import copy

from dataclasses import dataclass, field

from src.card import Card
from src.clue import Clue
from src.action import Action
from src.constants import ACTION, MAX_BOOM_NUM, MAX_CLUE_NUM, MAX_RANK, MAX_CARDS_PER_RANK
from src.utils import dump, printf


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
    num_remaining_cards: int = -1
    post_draw_turns: int = 0
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

    def initialize(self, num_players, start_player_index, hands):
        self.num_players = num_players
        self.start_player_index = start_player_index
        self.hands = hands
        self.num_remaining_cards = sum(sum(MAX_CARDS_PER_RANK[i]) for i in range(self.num_suits))
        for hand in hands:
            for card in hand:
                self.num_remaining_cards -= 1
                self.initial_cards.append(card)
    
    def next_snapshot(self, action: Action):
        """
        Return the next snapshot after taking the action.
        The action is assumed to be game-valid.
        """
        next_snapshot = Snapshot(
            clue_tokens=self.clue_tokens,
            boom_tokens=self.boom_tokens,
            num_suits=self.num_suits,
            num_players=self.num_players,
            play_pile=copy.deepcopy(self.play_pile),
            discard_pile=copy.deepcopy(self.discard_pile),
            hands=[copy.deepcopy(hand) for hand in self.hands],
            initial_cards=copy.deepcopy(self.initial_cards),
            action_history=copy.deepcopy(self.action_history),
        )
        next_snapshot._perform_action(action)
        next_snapshot.action_history.append(action)
        return next_snapshot

    """
    Get all game-valid actions for a player from a viewer's view.
    Game-valid means it is doable by the game rules, even if it means a boom.
    """
    def get_valid_actions(self, viewer_index: int, player_index: int) -> list:
        actions = []
        if self.is_end_status():
            # Game is over, no more actions allowed.
            return actions

        # Playing a card is always valid.
        for card in self.hands[player_index]:
            actions.append(Action(
                action_type=ACTION.PLAY.value,
                player_index=player_index,
                card=Card(card.order)))
        
        # Discarding a card is valid except clue tokens are full.
        if self.clue_tokens < 8:
            for card in self.hands[player_index]:
                actions.append(Action(
                    action_type=ACTION.DISCARD.value,
                    player_index=player_index,
                    card=Card(card.order)))
        
        # Without any clue tokens, no more clues can be given.
        if self.clue_tokens <= 0:
            return actions

        # All possible clues towards other players' hand are valid.
        for i in range(self.num_players):
            cards = self.hands[i]
            if i == player_index:
                # A player cannot clue themselves.
                continue
            if i == viewer_index:
                # It is theoretically possible to clue the viewer from the player, however,
                # from the viewer's perspective, it is unexpected.
                continue
            valid_ranks = []
            valid_suits = []
            for card in cards:
                if card.rank != -1 and card.rank not in valid_ranks:
                    valid_ranks.append(card.rank)
                if card.suit_index != -1 and card.suit_index not in valid_suits:
                    valid_suits.append(card.suit_index)
            for rank in valid_ranks:
                actions.append(Action(
                    action_type=ACTION.RANK_CLUE.value,
                    player_index=player_index,
                    clue=Clue(hint_type=ACTION.RANK_CLUE.value, giver_index=player_index, receiver_index=i, hint_value=rank)))
            for suit in valid_suits:
                actions.append(Action(
                    action_type=ACTION.COLOR_CLUE.value,
                    player_index=player_index,
                    clue=Clue(hint_type=ACTION.COLOR_CLUE.value, giver_index=player_index, receiver_index=i, hint_value=suit)))
        return actions

    def is_end_status(self) -> bool:
        # Boom tokens are used up.
        if self.boom_tokens <= 0:
            return True
        # All possible cards are played.
        if len(self.play_pile) == self._max_score_limit():
            return True
        # All cards are drawn and everyone finishes the final turn.
        if self.num_remaining_cards == 0 and self.post_draw_turns == self.num_players:
            return True
        return False

    def _max_score_limit(self) -> int:
        theoretical_max_score = self.num_suits * MAX_RANK
        if len(self.discard_pile) == 0:
            return theoretical_max_score

        discard_ranks = [[0] * (MAX_RANK + 1) for _ in range(self.num_suits)]
        for card in self.discard_pile:
            discard_ranks[card.suit_index][card.rank] += 1
        for suit in range(self.num_suits):
            for rank in range(1, MAX_RANK + 1):
                if discard_ranks[suit][rank] == MAX_CARDS_PER_RANK[suit][rank]:
                    theoretical_max_score -= (MAX_RANK - rank + 1)
                    break
        return theoretical_max_score
    
    def _perform_action(self, action: Action):
        if action.action_type == ACTION.DRAW.value:
            self._perform_draw(action)
            return

        if action.action_type == ACTION.PLAY.value:
            if action.boom:
                self._perform_boom(action)
            else:
                self._perform_play(action)
        elif action.action_type == ACTION.DISCARD.value:
            self._perform_discard(action)
        elif action.action_type == ACTION.COLOR_CLUE.value or action.action_type == ACTION.RANK_CLUE.value:
            self._perform_clue(action)

        if self.num_remaining_cards == 0:
            self.post_draw_turn += 1
        
    def _perform_draw(self, action: Action):
        self.hands[action.player_index].append(action.card)
        self.num_remaining_cards -= 1

    def _perform_play(self, action: Action):
        self.play_pile.append(self._remove_card_from_hand(action.player_index, action.card.order))
    
    def _perform_discard(self, action: Action):
        self.discard_pile.append(self._remove_card_from_hand(action.player_index, action.card.order))
        self.clue_tokens += 1
    
    def _perform_boom(self, action: Action):
        self.discard_pile.append(self._remove_card_from_hand(action.player_index, action.card.order))
        self.boom_tokens -= 1
    
    def _perform_clue(self, action: Action):
        self.clue_tokens -= 1

    def _remove_card_from_hand(self, player_index, order):
        hand = self.hands[player_index]

        card_index = -1
        for i, card in enumerate(hand):
            if card.order == order:
                card_index = i
                break

        if card_index == -1:
            printf(
                "error: unable to find card with order " + str(order) + " in "
                "the hand of player " + str(player_index)
            )
            return None

        card = copy.deepcopy(hand[card_index])
        del hand[card_index]
        return card
