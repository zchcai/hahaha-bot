"""Implementation of Hanabi client."""

# Imports (standard library)
import json

# Imports (3rd-party)
import websocket

# Imports (local application)
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.game_state import GameState
from src.utils import printf, dump


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
        self.handle_action(data["action"], data["tableID"])

        if state.current_player_index == state.our_player_index:
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
            card = self.remove_card_from_hand(state, player_index, order)
            if card is not None:
                # TODO: check expectation.
                state.play_stacks[card.suit_index] += 1

        elif data["type"] == "discard":
            player_index = data["playerIndex"]
            order = data["order"]
            card = self.remove_card_from_hand(state, player_index, order)
            if card is not None:
                # TODO Add the card to the discard stacks.
                # TODO: check expectation.
                pass

            # Discarding adds a clue. But misplays are represented as discards,
            # and misplays do not grant a clue.
            if not data["failed"]:
                state.clue_tokens += 1

        elif data["type"] == "clue":
            # Parse clue details.
            clue = Clue()
            clue.hint_type = 1 if data["clue"]["type"] == 1 else 2
            clue.hint_value = data["clue"]["value"]
            clue.giver_index = data["giver"]
            clue.receiver_index = data["target"]
            clue.turn = data["turn"]

            # Add clue into touched cards.
            cards = state.player_hands[clue.receiver_index]
            num_cards = len(cards)
            possible_play_mark = False

            # TODO: check discard slot firstly.
            # TODO: negative information tracking.
            # TODO: finesse
            for i in range(num_cards):
                # From draw slot to discard slot.
                card = cards[num_cards - i - 1]
                if card.order in data["list"]:
                    card.add_clue(clue)
                    if clue.hint_type == 1:
                        card.rank = clue.hint_value
                    elif clue.hint_type == 2:
                        card.suit_index = clue.hint_value
                        if possible_play_mark is False:
                            card.clues[-1].classification = 1
                            possible_play_mark = True
                        else:
                            card.clues[-1].classification = 2

            # Update game state: each clue costs one clue token.
            state.clue_tokens -= 1

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

        # Play cards if possible.
        for i in range(num_cards):
            # From draw slot to discard slot
            card = cards[num_cards - i - 1]
            if state.is_playable(card):
                self.play_card(card.order)
                return

        # Discard when neither a play nor a clue.
        if state.clue_tokens == 0:
            # There are no clues available, so discard our oldest unclued card.
            for i in range(num_cards):
                card = cards[i]
                if len(card.clues) == 0:
                    self.discard_card(card.order)
                    return
            # In a real game, it should not arrive here, however, if it does,
            # then we need to do something.
            self.play_card(cards[0].order)
            return

        # Target the next player.
        target_index = (state.our_player_index + 1) % len(state.player_names)
        printf(target_index)

        # Cards are added oldest to newest, so "draw slot" is the final
        # element in the list.
        target_hand = state.player_hands[target_index]
        for i in range(num_cards):
            card = target_hand[num_cards - i - 1]
            if len(card.clues) > 1:
                continue

            if len(card.clues) == 0:
                self.send(
                    "action",
                    {
                        "tableID": table_id,
                        "type": ACTION.RANK_CLUE,
                        "target": target_index,
                        "value": card.rank,
                    },
                )
            elif len(card.clues) == 1:
                existing_clue_type = card.clues[0].hint_type
                if existing_clue_type == 1:
                    self.send(
                        "action",
                        {
                            "tableID": table_id,
                            "type": ACTION.COLOR_CLUE,
                            "target": target_index,
                            "value": card.suit_index,
                        },
                    )
                elif existing_clue_type == 2:
                    self.send(
                        "action",
                        {
                            "tableID": table_id,
                            "type": ACTION.RANK_CLUE,
                            "target": target_index,
                            "value": card.rank,
                        },
                    )
            return


    # -----------
    # Subroutines
    # -----------

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

    def discard_card(self, card_order):
        self.send("action",
                  {
                      "tableID": self.current_table_id,
                      "type": ACTION.DISCARD,
                      "target": card_order,
                  },
                  )

    def play_card(self, card_order):
        self.send("action",
                  {
                      "tableID": self.current_table_id,
                      "type": ACTION.PLAY,
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

        card = hand[card_index]
        del hand[card_index]
        return card
