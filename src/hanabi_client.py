"""Implementation of Hanabi client."""

# Imports (standard library)
import copy
import json
import time

# Imports (3rd-party)
import websocket

# Imports (local application)
from src.action import Action
from src.card import Card
from src.clue import Clue
from src.constants import ACTION
from src.game import Game
from src.utils import printf, dump
from src.constants import MAX_CLUE_NUM


class HanabiClient:
    """The main implementation of a Hanabi client."""

    def __init__(self, url, cookie, username="robot1", debug=None):
        # Initialize all class variables.
        self.command_handlers = {}
        self.tables = {}
        self.current_table_id = None
        self.username = ""
        self.ws = None
        self.games = {}
        self.debug = debug
        self.username = username

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

    def websocket_message(self, _, message):
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

    def websocket_error(self, _, error):
        printf("Encountered a WebSocket error:", error)

    def websocket_close(self, _):
        printf("WebSocket connection closed.")

    def websocket_open(self, _):
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
                printf("Error when deciding action: ", e)
        elif command == "debug":
            self.print_debug_info()
        elif command == "create":
            self.chat_create()
        elif command == "terminate":
            self.chat_terminate()
        elif command == "invite":
            self.chat_invite()
        elif command == "start":
            self.chat_start()
        else:
            msg = "That is not a valid command."
            self.chat_reply(msg, data["who"])

    def chat_invite(self):
        for i in range(1, 5):
            name = "robot" + str(i)
            if name != self.username:
                self.chat_reply("/join", name)

    def chat_create(self):
        self.send(
            "tableCreate",
            {
                "name": "test game",
                "options": {
                    "VariantName": "No Variant",
                },
            },
        )

    def chat_start(self):
        table_id = self.current_table_id
        for table in self.tables.values():
            if not table["running"] and self.username in table["players"]:
                table_id = table["id"]
                break
        self.send(
            "tableStart",
            {
                "tableID": table_id,
            },
        )

    def chat_terminate(self):
        for table_id in self.tables.keys():
            self.send(
                "tableTerminate",
                {
                    "tableID": table_id,
                },
            )

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
        self.current_table_id = table_id

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
        game = Game()
        self.games[data["tableID"]] = game

        game.player_names = data["playerNames"]
        game.our_player_index = data["ourPlayerIndex"]

        # Initialize the hands for each player (an array of Cards).
        for _ in range(len(game.player_names)):
            game.player_hands.append([])

        # Initialize the play stacks.
        # https://raw.githubusercontent.com/Hanabi-Live/hanabi-live/refs/heads/main/packages/game/src/json/variants.json
        # No Variant:      0
        # Black (6 Suits):  2
        if data["options"]["variantName"] == "No Variant":
            game.num_suits = 5
        else:
            printf("error: Variant not supported: " + data)
            NotImplementedError("Variant not supported")

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
        game = self.games[data["tableID"]]

        # We just received a new action for an ongoing game.
        pre_turn = len(game.action_history)
        self.handle_action(data["action"], data["tableID"])
        post_turn = len(game.action_history)

        if (
            post_turn != pre_turn
            and game.current_player_index() == game.our_player_index
        ):
            self.decide_action(data["tableID"])

    def game_action_list(self, data):
        game = self.games[data["tableID"]]

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
        if game.current_player_index() == game.our_player_index:
            self.decide_action(data["tableID"])

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

    def handle_action(self, data, table_id):
        printf(f"debug: 'gameAction' of '{data['type']}' for table {table_id}")
        printf(f"debug: \t\t{data}")
        if data["type"] not in ["clue", "play", "draw", "discard"]:
            printf(f"skip unknown action type '{data['type']}'")
            return

        state = self.games[table_id]

        if data["type"] == "clue":
            clue_hint_type = ACTION.COLOR_CLUE.value
            if data["clue"]["type"] % ACTION.COLOR_CLUE.value != 0:
                clue_hint_type = ACTION.RANK_CLUE.value

            state.handle_action(
                Action(
                    action_type=clue_hint_type,
                    player_index=data["giver"],
                    clue=Clue(
                        hint_type=clue_hint_type,
                        hint_value=data["clue"]["value"],
                        giver_index=data["giver"],
                        receiver_index=data["target"],
                        turn=data["turn"],
                        touched_orders=data["list"],
                    ),
                )
            )
            return

        action_type = None
        boom = False
        if data["type"] == "play":
            action_type = ACTION.PLAY.value
        elif data["type"] == "draw":
            action_type = ACTION.DRAW.value
        elif data["type"] == "discard":
            if not data["failed"]:
                action_type = ACTION.DISCARD.value
            else:
                boom = True
                action_type = ACTION.PLAY.value

        state.handle_action(
            Action(
                action_type=action_type,
                boom=boom,
                player_index=data["playerIndex"],
                # A temporary Card object to pass information.
                # The actual card object will be retrieved from the game snapshot's player_hands.
                card=Card(
                    order=data["order"], suit_index=data["suitIndex"], rank=data["rank"]
                ),
            )
        )

    def decide_action(self, table_id=None):
        if table_id is None:
            table_id = self.current_table_id

        self.perform_action(self.games[table_id].decide_action())

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

    def color_clue(self, target, color):
        if self.debug is None:
            time.sleep(2)
        self.send(
            "action",
            {
                "tableID": self.current_table_id,
                "type": ACTION.COLOR_CLUE.value,
                "target": target,
                "value": color,
            },
        )

    def rank_clue(self, target, rank):
        if self.debug is None:
            time.sleep(2)
        self.send(
            "action",
            {
                "tableID": self.current_table_id,
                "type": ACTION.RANK_CLUE.value,
                "target": target,
                "value": rank,
            },
        )

    def discard_card(self, card_order):
        if self.debug is None:
            time.sleep(2)
        self.send(
            "action",
            {
                "tableID": self.current_table_id,
                "type": ACTION.DISCARD.value,
                "target": card_order,
            },
        )

    def play_card(self, card_order):
        if self.debug is None:
            time.sleep(2)
        self.send(
            "action",
            {
                "tableID": self.current_table_id,
                "type": ACTION.PLAY.value,
                "target": card_order,
            },
        )

    def perform_action(self, action: Action):
        if action.action_type == ACTION.PLAY.value:
            self.play_card(action.card.order)
        elif action.action_type == ACTION.DISCARD.value:
            self.discard_card(action.card.order)
        else:
            if action.clue.hint_type == ACTION.COLOR_CLUE.value:
                self.color_clue(action.clue.receiver_index, action.clue.hint_value)
            else:
                self.rank_clue(action.clue.receiver_index, action.clue.hint_value)
