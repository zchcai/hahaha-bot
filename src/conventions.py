"""Conventions implementation by functions of elimination."""

import json
import jsonpickle
import random
import re

from src.action import Action
from src.snapshot import Snapshot
from src.constants import ACTION
from src.utils import dump


def evaluate(snapshot: Snapshot, viewer_index, player_index):
    game_valid_actions = snapshot.get_valid_actions(
        viewer_index=viewer_index, player_index=player_index
    )
    sorted_actions = sorted(
        game_valid_actions,
        key=lambda action: _evaluate_action(
            snapshot, action, viewer_index, player_index
        ),
        reverse=True,
    )
    return sorted_actions


def _evaluate_action(snapshot, action, viewer_index, player_index):
    if action.action_type == ACTION.PLAY.value:
        # check the status of this card
        # For known cards, check whether it is a boom.
        # For half-known cards, check whether it is playable.
        # For unknown cards, check the confidence of playable.
        return 0
    if action.action_type == ACTION.DISCARD.value:
        return 1
    if action.action_type == ACTION.COLOR_CLUE.value:
        return 2
    if action.action_type == ACTION.RANK_CLUE.value:
        return 3
    return random.randint(0, 100)
