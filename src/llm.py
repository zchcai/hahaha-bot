import json
import jsonpickle
from openai import OpenAI
from ollama import chat, ChatResponse
import random
import re

from src.action import Action
from src.snapshot import Snapshot
from src.constants import ACTION
from src.utils import dump

HANABI_RULES_PROMPT="""Hanabi is a cooperative card game where players work together to create a spectacular fireworks display by playing cards in sequence by color. Follow these guidelines strictly:

1. Game Setup & Components

The deck consists of cards in five colors (Red, Green, Blue, Yellow and Purple), each with numbers typically ranging from 1 to 5 (i.e., rank).
The distribution of cards per number is predetermined: multiple copies of low-number cards and a single copy of high-number cards.
Each player's cards are held facing outwards, meaning players can see everyone's cards except their own.
It starts with 8 clue tokens and 3 boom tokens.
For 2-3 players game, each player starts with 5 cards; while for 4-5 players', they hold 4 cards respectively.

2. Objective

The goal is to collectively build five fireworks (one per color) in sequential order, starting with 1 and ending with 5.
Players must work together using limited communication to play the correct cards in the correct order.

3. Gameplay Mechanics

3.1 Hints (Clues):

Players have a limited pool of hint tokens. On their turn, a player may give a hint to another player about the cards in their hand.
Hints can indicate either a color or a number, and must reveal all instances of that color or number in the target player's hand.

3.2 Playing a Card:

A player may attempt to play a card from their hand to a fireworks pile.
A card can only be played if it continues the sequence for that color (i.e., the next number in order), and players don't need to claim the card details before playing.
If played correctly, the card is added to the corresponding fireworks pile. If incorrect, the card is discarded, and a boom token is used.

3.3 Discarding a Card:

A player may choose to discard a card from their hand. This returns one hint token to the pool.
The discarded card is placed in a discard pile, making it unavailable for future play.

Note: when the clue tokens are 8, for example, a beginning of a game, the player cannot discard.

4. Game End Conditions

The game ends in one of three ways:

4.1 The players successfully complete all five fireworks (perfect score).
4.2 The players use up all 3 boom tokens, ending the game immediately and the score is zero.
4.3 The deck is exhausted and each player has taken one final turn.

The final score is determined by the sum of the highest number in each completed fireworks pile.

5. Additional Considerations

- Communication is limited strictly to the approved hint mechanism. No other information about the cards (such as their value or color) may be discussed.
- Encourage strategic decision-making, teamwork, and careful management of hint tokens.
- Clarify any ambiguities by referring back to these rules, ensuring fair play and consistent application throughout the game.

"""

CONVENTION_PROMPT="""Now, to play this game in a professional way, please follow the conventions below:

1. Terms:

- Discard slot is the oldest untouched card. When players find nothing to do, they should discard from that position first.
- Finesse slot or draw slot is the most recent card. When players find themselves demanded to play a card but no clued cards can help, then they play the draw slot.
- Color Clue: a clue touches all cards with a color.
- Number Clue: a clue touches all cards with a number.

2. Principles

- Good touch principle: clue-givers should try to not give clue duplicate cards, and clue-receivers should assume all touched cards are uniquely useful, unless truth information conflicts.
- A clue is either preserved as a play clue or a save clue:
    - Play Clue: it means the most recent hinted card is playable or there is a playable path towards it.
    - Save Clue: it should be a Rank (Number) Clue and touches the discard slot. Clue-receiver should first check whether the discard slot can be a unique card to save. Otherwise, this Rank Clue is a Play Clue.

3. Conventions

- Color clue means Play.
- Number clue not touching the discard slot is also a Play Clue.
- Number clue touching the discard slot might tell the receiver that discard slot needs to save at hand.
- Play Clue hints the most recent touched card is playable and the remaining is good touch save.

3.1 **Finesse** (most important)

Finesse means, a player's draw slot card, though not clued, can also be treated in an actionable sequence.
For example, if Player 1 is the start player, they find Player 2's draw slot is Blue 1, and Player 4's second slot is Blue 2, then they can consider directly give Player 4 a Color Clue, Blue.
Why this will work? This because after this clue, Player 2 will start to think, why Player 1 tells Player 4 Blue 2 is playable while no Blue 1 is clued yet.
Then they refer to this convention and realize their finesse slot (draw slot) must be the card to help Player 4's Blue 2 playable. Thus, Player 2 will blindly play their draw slot.
And immediately after Player 2 plays the draw slot blindly, Player 4 realizes their Blue card is not Blue 1 but Blue 2.

Finesse convention really improves the game efficiency because it will increase the number of cards to play by less clues.
The deduction reasoning is also very helpful.

Now, please look at this snapshot of this game, and give what you should do on the current player's view and give the action you suggest in the following format:
- Play <card no>
- Discard <card no>
- Color Clue <color> <target_player_no>
- Rank Clue <rank> <target_player_no>

Current Snapshot:

"""

POST_PROMPT = """
Please do this step by step: first understand the game rules, what is allowed and what is forbiddened, second understand the conventions, third read the snapshot and parse the world state, at last do a detailed analysis on which action to take.
For example, giving Number Clue 1 to Player 2 is violating Good touch principle, thus we should not do. Cluing 1 to player 3 is ok but could you find a better clue in this game opening?
"""

def call_llm(snapshot: Snapshot, model="deepseek-r1") -> str:
    serialized = jsonpickle.encode(snapshot)
    text = json.dumps(json.loads(serialized), indent=2)
    # Debug translation
    text = """
- **Player 0 (me):** All 4 cards are unknown because my own hand isn't visible to myself.
- **Player 1:** (finesse slot) Blue 1, Green 2, Purple 3, Green 2 (discard slot)
- **Player 2:** (finesse slot) Purple 4, Red 2, Red 1, Red 1 (discard slot)
- **Player 3:** (finesse slot) Red 3, Yellow 1, Blue 2, Green 1 (discard slot)

The play pile, discard pile, action history are all empty. Remaining clue tokens are 8 (max) and boom tokens are 3 (max). This is the beginning of a game. Player 0 (me) needs to decide what to do.
"""
    prompt = HANABI_RULES_PROMPT + CONVENTION_PROMPT + text + POST_PROMPT
    try:
        res = ask_deepseek(model, prompt)
        return res
    except Exception as e:
        print(f"Error in calling LLM: {e}")
        return "The original prompt is: " + prompt

# https://github.com/ChristianD37/YoutubeTutorials/blob/master/DeepSeekPython/deepseek_tutorial.ipynb
def ask_deepseek(model, user_prompt, system_prompt='', deep_think = True, print_log = True):
    response: ChatResponse = chat(model=model, messages=[
        {'role' : 'system', 'content' : system_prompt},
        {'role': 'user','content': user_prompt}
    ])
    response_text = response['message']['content']
    if print_log: print(response_text)
    # Extract everything inside <think>...</think> - this is the Deep Think
    think_texts = re.findall(r'<think>(.*?)</think>', response_text, flags=re.DOTALL)
    # Join extracted sections (optional, if multiple <think> sections exist)
    think_texts = "\n\n".join(think_texts).strip()
    # Exclude the Deep Think, and return the response
    clean_response= re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()

    # Return either the context, or a tuple with the context and deep think
    return clean_response if not deep_think else (clean_response, think_texts)
