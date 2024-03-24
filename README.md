# Hahaha-bot

**Current Progress**: █░░░░░░░░░ 1%

This repo will implement a mainly [rule-based](https://docs.google.com/document/d/1u4PzGPzN3h79s0QLlejsM6-_m80oemAnbhTrTwXmOL0/edit) robot to play with humans. It is forked from [Hanabi-Live/hanabi-live-bot](https://github.com/Hanabi-Live/hanabi-live-bot) because we want to make the use of [hanab.live](https://github.com/Hanabi-Live//hanabi-live)'s powerful UI features to play, watch and review Hanabi games interactively with robots in a more human-friendly way.

## Setup Instructions

- Install the dependencies:
  - `pip install -r requirements.txt`
- Set up environment variables:
  - `cp .env_template src/.env`
  - `vim src/.env`
- Run it:
  - `python src/main.py`
- In a browser, log on to the website and start a new table.
- In the pre-game chat window, send a private message to the bot(s) in order to get them to join you:
  - `/msg [robot_username] /join`
- Then, start the game and ~~play~~ debug! :sweat_smile:
