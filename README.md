# Hahaha-bot

**Current Progress**: █░░░░░░░░░ 2%

This repo will implement a mainly [rule-based](https://docs.google.com/document/d/1u4PzGPzN3h79s0QLlejsM6-_m80oemAnbhTrTwXmOL0/edit) robot to play with humans. It is forked from [Hanabi-Live/hanabi-live-bot](https://github.com/Hanabi-Live/hanabi-live-bot) because we want to make the use of [hanab.live](https://github.com/Hanabi-Live//hanabi-live)'s powerful UI features to play, watch and review Hanabi games interactively with robots in a more human-friendly way.

## Setup Instructions

- Install the dependencies:
  - `pip install -r requirements.txt`
- Set up environment variables:
  - `cp .env_template .env`
  - `vim .env`
- Run it:
  - `python main.py`
- In a browser, log on to the website and start a new table.
- In the pre-game chat window, send a private message to the bot(s) in order to get them to join you:
  - `/msg [robot_username] /join`
- During the game, sometimes the bot forgets to play, then we can send a message to remind them:
  - `/msg [robot_username] /please`
- Then, start the game and ~~play~~ debug! :sweat_smile:
  - We can use this to let it print debug information: 
    - `/msg [robot_username] /debug`

## Development Tips

### [Live Test Coverage](https://jasonstitt.com/perfect-python-live-test-coverage)
- Run `pip3 install pytest-watch` and open a terminal to run `pytest-watch`. It will automatically check the unit test code coverage when files get changed.
- (Optional) If using VS Code, then install [Coverage Gutters](https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters) and run `Coverage Gutters: Watch`. It will read the auto-updated `lcov.info` file and update the coverage lines accordingly.
