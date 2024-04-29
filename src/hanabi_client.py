"""Implementation of Hanabi client."""

# Imports (standard library)
import copy
import json

# Imports (3rd-party)
import websocket

# Imports (local application)
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.game_state import GameState
from src.utils import printf, dump
from src.constants import MAX_CLUE_NUM


class HanabiClient:
    """The main implementation of a Hanabi client."""

    def __init__(self, url, cookie):
        # Initialize all class variables.
        self.command_handlers = {}
        self.tables = {}
        self.current_table_id = None
        self.username = ""
        self.ws = None
        self.games = {}

        # Initialize the website command handlers (for the lobby).
        self.command_handlers["welcome"] = self.welcome
        self.command_handlers["warning"] = self.warning
        self.command_handlers["error"] = self.error
        self.command_handlers["chat"] = self.chat
        self.command_handlers["table"] = self.table
        self.command_handlers["tableList"] = self.table_list
        self.command_handlers["tableGone"] = self.table_gone
        self.command_handlers["tableStart"] = self.table_start

        # Initialize the website command handlers (for the game).
        self.command_handlers["init"] = self.init
        self.command_handlers["gameAction"] = self.game_action
        self.command_handlers["gameActionList"] = self.game_action_list
        self.command_handlers["databaseID"] = self.database_id

        # Start the WebSocket client.
        printf('Connecting to "' + url + '".')

        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.websocket_message,
            on_error=self.websocket_error,
            on_open=self.websocket_open,
            on_close=self.websocket_close,
            cookie=cookie,
        )
        self.ws.run_forever()

    def print_debug_info(self):
        printf("==============DEBUG===============\n")
        dump(self.tables)
        dump(self.games[self.current_table_id])
        printf("==============DEBUG===============\n")

    # ------------------
    # WebSocket Handlers
    # ------------------

    def websocket_message(self, ws, message):
        """
        # WebSocket messages from the server come in the format of:
        # commandName {"fieldName":"value"}
        # For more information, see:
        # https://github.com/Hanabi-Live/hanabi-live/blob/master/server/src/websocket_message.go
        """
        result = message.split(" ", 1)  # Split it into two things
        if len(result) != 1 and len(result) != 2:
            printf("error: received an invalid WebSocket message:")
            printf(message)
            return

        command = result[0]
        try:
            data = json.loads(result[1])
        except TypeError:
            printf(
                'error: the JSON data for the command of "' + command + '" was invalid'
            )
            return

        if command in self.command_handlers:
            printf('debug: got command "' + command + '"')
            try:
                self.command_handlers[command](data)
            except Exception as e:
                printf('error: command handler for "' + command + '" failed:', e, data)
                return
        else:
            printf('debug: ignoring command "' + command + '"')

    def websocket_error(self, ws, error):
        printf("Encountered a WebSocket error:", error)

    def websocket_close(self, ws):
        printf("WebSocket connection closed.")

    def websocket_open(self, ws):
        printf("Successfully established WebSocket connection.")

    # --------------------------------
    # Website Command Handlers (Lobby)
    # --------------------------------

    def welcome(self, data):
        # The "welcome" message is the first message that the server sends us
        # once we have established a connection. It contains our username,
        # settings, and so forth.
        self.username = data["username"]

    def error(self, data):
        # Either we have done something wrong, or something has gone wrong on
        # the server.
        printf(data)

    def warning(self, data):
        # We have done something wrong.
        printf(data)

    def chat(self, data):
        # We only care about private messages.
        if data["recipient"] != self.username:
            return

        # We only care about private messages that start with a forward slash.
        if not data["msg"].startswith("/"):
            return
        data["msg"] = data["msg"][1:]  # Remove the slash.

        # We want to split it into two things.
        result = data["msg"].split(" ", 1)
        command = result[0]

        if command == "join":
            self.chat_join(data)
        elif command == "please":
            try:
                self.decide_action(self.current_table_id)
            except Exception as e:
                printf('Error when deciding action: ', e)
        elif command == "debug":
            self.print_debug_info()
        else:
            msg = "That is not a valid command."
            self.chat_reply(msg, data["who"])

    def chat_join(self, data):
        # Someone sent a private message to the bot and requested that we join
        # their game. Find the table that the current user is currently in.
        table_id = None
        for table in self.tables.values():
            # Ignore games that have already started (and shared replays).
            if table["running"]:
                continue

            if data["who"] in table["players"]:
                if len(table["players"]) == 6:
                    msg = "Your game is full; no room for me to join the game."
                    self.chat_reply(msg, data["who"])
                    return

                table_id = table["id"]
                break

        if table_id is None:
            msg = "Please create a table first before requesting that I join your game."
            self.chat_reply(msg, data["who"])
            return

        self.send(
            "tableJoin",
            {
                "tableID": table_id,
                "password": "",
            },
        )

    def table(self, data):
        self.tables[data["id"]] = data

    def table_list(self, data_list):
        for data in data_list:
            self.table(data)

    def table_gone(self, data):
        del self.tables[data["tableID"]]

    def table_start(self, data):
        # The server has told us that a game that we are in is starting. So,
        # the next step is to request some high-level information about the
        # game (e.g. number of players). The server will respond with an "init"
        # command.
        self.current_table_id = data["tableID"]
        self.send(
            "getGameInfo1",
            {
                "tableID": data["tableID"],
            },
        )

    # -------------------------------
    # Website Command Handlers (Game)
    # -------------------------------

    def init(self, data):
        # At the beginning of the game, the server sends us some high-level
        # data about the game, including the names and ordering of the players
        # at the table.

        # Make a new game state and store it on the "games" dictionary.
        state = GameState()
        self.games[data["tableID"]] = state

        state.player_names = data["playerNames"]
        state.our_player_index = data["ourPlayerIndex"]

        # Initialize the hands for each player (an array of Cards).
        for _ in range(len(state.player_names)):
            state.player_hands.append([])

        # Initialize the play stacks.
        """
        This is hard coded to 5 because there 5 suits in a no variant game
        The website supports variants that have 3, 4, and 6 suits
        TODO This code should compare "data['variant']" to the "variants.json"
        file in order to determine the correct amount of suits
        https://raw.githubusercontent.com/Zamiell/hanabi-live/master/public/js/src/data/variants.json
        """
        num_suits = 5
        for _ in range(num_suits):
            state.play_stacks.append(0)

        # At this point, the JavaScript client would have enough information to
        # load and display the game UI. For our purposes, we do not need to
        # load a UI, so we can just jump directly to the next step. Now, we
        # request the specific actions that have taken place thus far in the
        # game (which will come in a "gameActionList").
        self.send(
            "getGameInfo2",
            {
                "tableID": data["tableID"],
            },
        )

    def game_action(self, data):
        state = self.games[data["tableID"]]

        # We just received a new action for an ongoing game.
        pre_turn = state.turn
        self.handle_action(data["action"], data["tableID"])
        post_turn = state.turn

        if post_turn != pre_turn and state.current_player_index == state.our_player_index:
            self.decide_action(data["tableID"])

    def game_action_list(self, data):
        state = self.games[data["tableID"]]

        # We just received a list of all of the actions that have occurred thus
        # far in the game.
        # When the game just starts, they are the drawing actions.
        for action in data["list"]:
            self.handle_action(action, data["tableID"])

        # Let the server know that we have finished "loading the UI" (so that
        # our name does not appear as red / disconnected).
        self.send(
            "loaded",
            {
                "tableID": data["tableID"],
            },
        )

        # Start the game if we are the first player.
        if state.current_player_index == state.our_player_index:
            self.decide_action(data["tableID"])

    def handle_action(self, data, table_id):
        printf(f"debug: 'gameAction' of '{data['type']}' for table {table_id}")
        printf(f"debug: \t\t{data}")

        state = self.games[table_id]

        if data["type"] == "draw":
            # Add the newly drawn card to the player's hand.
            state.player_hands[data["playerIndex"]].append(
                Card(
                    order=data["order"],
                    suit_index=data["suitIndex"],
                    rank=data["rank"]))

        elif data["type"] == "play":
            # This is a successful play.
            # A boom will be classified as a discard.
            player_index = data["playerIndex"]
            order = data["order"]
            played_suit_index = data["suitIndex"]
            played_rank = data["rank"]
            card = self.remove_card_from_hand(state, player_index, order)
            if card is not None:
                # TODO: check expectation.
                state.play_stacks[played_suit_index] = played_rank

        elif data["type"] == "discard":
            player_index = data["playerIndex"]
            order = data["order"]
            card = self.remove_card_from_hand(state, player_index, order)
            if card is not None:
                # TODO: check expectation, especially at a boom.
                card.rank = data["rank"]
                card.suit_index = data["suitIndex"]
                state.discard_pile.append(card)

            # Discarding adds a clue. But misplays are represented as discards,
            # and misplays do not grant a clue.
            if not data["failed"]:
                state.clue_tokens += 1

        elif data["type"] == "clue":
            # Parse clue details.
            clue = Clue(
                hint_type=1 if data["clue"]["type"] == 1 else 2,
                hint_value=data["clue"]["value"],
                giver_index=data["giver"],
                receiver_index=data["target"],
                turn=data["turn"],
                touched_orders=data["list"]
            )

            # Add clue into touched cards.
            cards = state.player_hands[clue.receiver_index]

            # Exception: special handling for 1s.
            if clue.hint_type == 1 and clue.hint_value == 1:
                # all 1s are playable.
                clue.classification = 1
                for card in cards:
                    if card.order in clue.touched_orders:
                        card.add_clue(clue)
                    else:
                        card.add_negative_info(clue)

                # Update game state: each clue costs one clue token.
                state.clue_tokens -= 1
                return

            # First, we need to see whether this is a save clue.
            discard_slot = state.current_discard_slot(clue.receiver_index)
            double_clued_cards = state.double_clued_cards(clue.receiver_index, clue)

            if (discard_slot is not None and discard_slot.order in clue.touched_orders
                and clue.hint_type == 1):
                # The discard slot is touched!
                possible_save_mark = True
                if clue.hint_value != 5:
                    possible_save_mark = False
                    for discarded_card in state.discard_pile:
                        if discarded_card.rank == clue.hint_value:
                            # TODO: remove the dup situation.
                            # This is a critical save.
                            possible_save_mark = True
                            break
                if possible_save_mark:
                    # check whether the left-most double clued card is playable.
                    if len(double_clued_cards) > 0:
                        focused_card = double_clued_cards[-1]
                        if state.is_playable(focused_card):
                            clue.classification = 1
                            focused_card.add_clue(clue)

                            # For all other cards, assign save mark.
                            clue.classification = 2
                            for card in cards:
                                if card.order not in clue.touched_orders:
                                    card.add_negative_info(clue)
                                else:
                                    if card.order != focused_card.order:
                                        card.add_clue(clue)
                            # Update game state: each clue costs one clue token.
                            state.clue_tokens -= 1
                            return

                    # otherwise, all cards are marked as save.
                    clue.classification = 2
                    for card in cards:
                        if card.order in clue.touched_orders:
                            card.add_clue(clue)
                        else:
                            card.add_negative_info(clue)

                    # Update game state: each clue costs one clue token.
                    state.clue_tokens -= 1
                    return

            # TODO: finesse
            # Second, determine the single focus of this play clue.
            # if no double clued, then the focus is the left-most touched card.
            play_focus_card_order = max(clue.touched_orders)

            if len(double_clued_cards) > 0:
                # one card is double clued.
                # if this card is playable, then this is a play clue.
                # otherwise, ignore it.

                # We want to make sure the newly playable card is the focus.
                focused_card = double_clued_cards[-1]
                pending_focused_card = copy.deepcopy(focused_card)
                pending_focused_card.add_clue(clue)
                if state.is_playable(pending_focused_card):
                    play_focus_card_order = focused_card.order

            for card in cards:
                if card.order in clue.touched_orders:
                    if card.order == play_focus_card_order:
                        clue.classification = 1
                    else:
                        clue.classification = 2
                    card.add_clue(clue)
                else: # append negative information
                    card.add_negative_info(clue)

            # Update game state: each clue costs one clue token.
            state.clue_tokens -= 1
            return

        elif data["type"] == "turn":
            # A turn is comprised of one or more game actions (e.g. play +
            # draw). The turn action will be the final thing sent on a turn,
            # which also includes the index of the new current player.
            # TODO: This action may be removed from the server in the future
            # since the client is expected to calculate the turn on its own
            # from the actions.
            state.turn = data["num"]
            state.current_player_index = data["currentPlayerIndex"]

    def database_id(self, data):
        # Games are transformed into shared replays after they are completed.
        # The server sends a "databaseID" message when the game has ended. Use
        # this as a signal to leave the shared replay.
        self.send(
            "tableUnattend",
            {
                "tableID": data["tableID"],
            },
        )

        # Delete the game state for the game to free up memory.
        del self.games[data["tableID"]]

    # ------------
    # AI functions
    # ------------

    def decide_action(self, table_id=None):
        """The main logic to determine actions to do."""

        if table_id is None:
            table_id = self.current_table_id
        state = self.games[table_id]

        # The server expects to be told about actions in the following format:
        # https://github.com/Hanabi-Live/hanabi-live/blob/main/server/src/command_action.go

        cards = state.player_hands[state.our_player_index]
        num_cards = len(cards)

        # Decide what to do.
        # TODO: first react to urgent situations.

        # Check if any players' discard slot needs to be saved.
        for player in range(len(state.player_hands)):
            if player == state.our_player_index:
                continue
            discard_slot = state.current_discard_slot(player)
            if discard_slot is not None and state.is_critical(discard_slot):
                if state.will_not_discard(player):
                    continue

                # We need to save them!
                # TODO: we don't need to save them if they have playable cards to clue or they have cards to play now.
                if state.clue_tokens > 0:
                    self.rank_clue(player, discard_slot.rank)
                else:
                    # Be creative!
                    my_discard_slot = state.current_discard_slot(state.our_player_index)
                    if my_discard_slot is not None:
                        self.discard_card(my_discard_slot.order)
                    else:
                        self.play_card(cards[-1].order)
                return

        # Play cards if possible.
        for i in range(num_cards):
            # From draw slot to discard slot
            card = cards[num_cards - i - 1]
            if state.is_playable(card):
                self.play_card(card.order)
                return

        # Discard when neither a play nor a clue.
        if state.clue_tokens <= 0:
            state.clue_tokens = 0
            self.try_discard(cards)
            return

        # TODO: don't clue already clued cards.
        # Try to clue immediate playable cards by color clue or rank clue.
        # First, search all playable candidates.
        num_players = len(state.player_names)
        immediate_playable_cards_per_player = []
        for player in range(num_players):
            immediate_playable_cards_per_player.append([])
            if player == state.our_player_index:
                continue
            for card in state.player_hands[player]:
                if state.is_playable(card):
                    immediate_playable_cards_per_player[player].append(card)
            if len(immediate_playable_cards_per_player[player]) == 0:
                # no immediate playable card for this player
                continue

            # Second, check each candidate one by one.
            for playable_card in immediate_playable_cards_per_player[player]:
                target_color = playable_card.suit_index
                target_rank = playable_card.rank

                # Is it already been clued or not?
                if len(playable_card.clues) > 0:
                    # Is it given a play clue?
                    if playable_card.clues[-1].classification == 1:
                        continue
                    # Otherwise, we just double clue it with different clue.
                    if playable_card.clues[-1].hint_type == 1:
                        self.color_clue(player, target_color)
                    else:
                        self.rank_clue(player, target_rank)
                    return

                # Can we give color clue or rank clue?
                can_give_color_clue = True
                can_give_rank_clue = True
                # First check whether there is any card left to it.
                for i in range(num_cards):
                    potential_touched_card = state.player_hands[player][i]
                    if potential_touched_card.suit_index == target_color:
                        # if the order is larger, it means it is left to it.
                        if potential_touched_card.order > playable_card.order:
                            can_give_color_clue = False
                    if potential_touched_card.rank == target_rank:
                        if potential_touched_card.order > playable_card.order:
                            can_give_rank_clue = False

                # For playable cards, color clue is better than rank clue.
                if can_give_color_clue:
                    self.color_clue(player, target_color)
                    return
                if can_give_rank_clue:
                    self.rank_clue(player, target_rank)
                    return

        # Nothing we can do, so discard.
        self.try_discard(cards)
        return

    # -----------
    # Subroutines
    # -----------

    def try_discard(self, cards):
        state = self.games[self.current_table_id]

        if state.clue_tokens == MAX_CLUE_NUM:
            # The idea is to give highly possible trash 1s or save 5s.
            for i in [1, 5, 2, 3, 4]:
                for j, hand in enumerate(state.player_hands):
                    if j == state.our_player_index:
                        continue
                    for card in hand:
                        if card.rank == i:
                            self.rank_clue(j, i)
                            return

        # Discard trash cards firstly.
        for card in cards:
            if self.games[self.current_table_id].is_trash(card):
                self.discard_card(card.order)
                return

        # Then oldest unclued card.
        for card in cards:
            if len(card.clues) == 0:
                self.discard_card(card.order)
                return

        self.play_card(cards[-1].order)
        return

    def chat_reply(self, message, recipient):
        self.send(
            "chatPM",
            {
                "msg": message,
                "recipient": recipient,
                "room": "lobby",
            },
        )

    def send(self, command, data):
        if not isinstance(data, dict):
            data = {}
        self.ws.send(command + " " + json.dumps(data))
        printf(f'debug: sent command "{command}": {data}')

    def color_clue(self, target, color):
        self.send("action",
                  {
                      "tableID": self.current_table_id,
                      "type": ACTION.COLOR_CLUE.value,
                      "target": target,
                      "value": color,
                  },
        )

    def rank_clue(self, target, rank):
        self.send("action",
                  {
                      "tableID": self.current_table_id,
                      "type": ACTION.RANK_CLUE.value,
                      "target": target,
                      "value": rank,
                  },
        )

    def discard_card(self, card_order):
        self.send("action",
                  {
                      "tableID": self.current_table_id,
                      "type": ACTION.DISCARD.value,
                      "target": card_order,
                  },
        )

    def play_card(self, card_order):
        self.send("action",
                  {
                      "tableID": self.current_table_id,
                      "type": ACTION.PLAY.value,
                      "target": card_order,
                  },
        )

    def remove_card_from_hand(self, state, player_index, order):
        hand = state.player_hands[player_index]

        card_index = -1
        for i, card in enumerate(hand):
            if card.order == order:
                card_index = i
                break

        if card_index == -1:
            printf(
                "error: unable to find card with order " + str(order) + " in"
                "the hand of player " + str(player_index)
            )
            return None

        card = copy.deepcopy(hand[card_index])
        del hand[card_index]
        return card
