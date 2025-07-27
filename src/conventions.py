"""Conventions implementation by functions of elimination."""

import json
import jsonpickle
import random
from typing import List, Optional
import re

from src.action import Action
from src.snapshot import Snapshot
from src.constants import ACTION, Status
from src.utils import dump


def check_convention(snapshot: Snapshot, action: Action, viewer_index: int) -> bool:
    player_index = action.player_index
    if viewer_index is None:
        viewer_index = player_index

    snapshot.recalculate_trash_cards(player_index, viewer_index)

    if action.action_type == ACTION.PLAY.value:
        pending_play = snapshot.get_card_from_hand(
            player_index=player_index, order=action.card.order
        )
        if pending_play.status == Status.PLAYABLE_KNOWN_BY_PLAYER:
            return True
        return False

    if action.action_type == ACTION.DISCARD.value:
        pending_discard = snapshot.get_card_from_hand(
            player_index=player_index, order=action.card.order
        )
        if pending_discard.status == Status.TRASH_KNOWN_BY_PLAYER:
            return True
        if pending_discard.status == Status.UNSPECIFIED:
            return True  # possibly ok, normal discard
        return False

    # The main check for clues.
    receiver_index = action.clue.receiver_index
    clue = action.clue
    clued_cards = [
        snapshot.get_card_from_hand(receiver_index, i) for i in clue.touched_orders
    ]
    current_hints_table = snapshot.hints_table()
    played_ranks_per_suit = snapshot.played_ranks()
    for card in clued_cards:
        if card.suit_index != -1 and card.rank != -1:
            current_hints_table[card.suit_index][card.rank] += 1
            if current_hints_table[card.suit_index][card.rank] > 1:
                # Duplicated card gets clued.
                # TODO: sometimes this is OK.
                return False
            if played_ranks_per_suit[card.suit_index] >= card.rank:
                # Garbage card gets touched.
                # TODO: sometimes this is OK.
                return False
        if card.status in (
            Status.PLAYABLE_KNOWN_BY_PLAYER,
            Status.TRASH_KNOWN_BY_PLAYER,
        ):
            # Redundant clue for a known card.
            # TODO: sometimes this is OK.
            return False
    # It passes the normal convention check rules.
    return True


def evaluate(
    snapshot: Snapshot, viewer_index, player_index, remaining_search_level: int = 1
) -> List[Action]:
    """Given a snapshot, return a sorted list of actions."""
    game_valid_actions: List[Action] = snapshot.get_valid_actions(
        viewer_index=viewer_index, player_index=player_index
    )
    normal_applicable_actions: List[Action] = [
        action
        for action in game_valid_actions
        if check_convention(snapshot, action, viewer_index)
    ]
    if len(normal_applicable_actions) < 1:
        return normal_applicable_actions

    for action in normal_applicable_actions:
        action.score = evaluate_action(
            snapshot, action, viewer_index, remaining_search_level
        )

    return sorted(
        normal_applicable_actions, key=lambda action: action.score, reverse=True
    )


def evaluate_action(
    snapshot: Snapshot,
    action: Action,
    viewer_index: int,
    remaining_search_level: int = 1,
):
    """This function will do a limited layer of search to determine the score of one action, based
    on a viewer's perspective at a specific snapshot.

    The algorithm is a recursive search until reaching the search level:
    1. Generate the next snapshot based on convention rules.
      - If a boom occurs, return negative score.
    2. Determine the next player's action.
      - If no actions available, return negative score.

    Returns:
        int: the evaluation score.
    """
    if remaining_search_level <= 0:
        return 0

    remaining_search_level -= 1
    next_snapshot = snapshot.next_snapshot(action, viewer_index)

    # Check annotation validation. Basically, will we give a wrong information in the next snapshot?

    for player in range(next_snapshot.num_players):
        for card in next_snapshot.hands[player]:
            status = card.status
            if status == Status.USEFUL and not snapshot.is_useful(card):
                # Wrong annotation and then the score should be negative.
                return -1

    next_player_index = (action.player_index + 1) % snapshot.num_players
    sorted_actions = evaluate(
        next_snapshot,
        viewer_index=viewer_index,
        player_index=next_player_index,
        remaining_search_level=remaining_search_level,
    )
    if len(sorted_actions) < 1:
        # Nothing can be done. Then the score is negative.
        return -1
    # Use the cumulative score as the parent score.
    return sum(action.score for action in sorted_actions)
