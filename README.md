# Hahaha-bot

**Current Progress**: ██░░░░░░░░ 20%

This repo will implement a mainly [rule-based](https://docs.google.com/document/d/1u4PzGPzN3h79s0QLlejsM6-_m80oemAnbhTrTwXmOL0/edit) robot to play with humans. It is forked from [Hanabi-Live/hanabi-live-bot](https://github.com/Hanabi-Live/hanabi-live-bot) because we want to make the use of [hanab.live](https://github.com/Hanabi-Live//hanabi-live)'s powerful UI features to play, watch and review Hanabi games interactively with robots in a more human-friendly way.

## Setup Instructions

### Initial Setup
- Install the latest Python and confirm its version:
  ```sh
  $ py --version
  Python 3.12.1
  ```

- Creating virtual environments:
  ```sh
  $ cd hahaha-bot
  $ py -m venv .venv
  ```

- Enter into the virtual environment:
  - Windows: `./.venv/Scripts/activate`

- Install the dependencies:
  - `pip3.13 install -r requirements.txt`

- Set up environment variables:
  - `cp .env_template .env`
  - `vim .env`

### How to Run

- Run some robots:
  - `py main.py`
  - `py main.py <robot_username_(password)_2> <robot_username_(password)_3> ...`
- In a browser, log on to the website.

#### Manual
- Start a new table and enter into the room's chat panel.
- `/msg [robot_username] /join`: tell a robot join this table.
- During the game, sometimes the bot forgets to play, then we can send a message to remind them:
  - `/msg [robot_username] /please`
  - We can use this to let it print debug information: 
    - `/msg [robot_username] /debug`

Then, start the game and ~~play~~ debug! :sweat_smile:

#### Robots Auto-play

- Enter into the lobby chat panel.
- (Optional) `/msg robot1 /terminate`: terminate any existing games.
- `/msg robot1 /create`: create a room, default as 'No Variant'.
- `/msg robot1 /invite`: send invitation to robotX, X = 1, 2, 3, 4.
- `/msg robot1 /start`: start the game.

Then ~~enjoy~~ watch their game as a viewer!

## Development Tips

### [Live Test Coverage](https://jasonstitt.com/perfect-python-live-test-coverage)
- Complete the initial setup.
- Open a terminal to run `pytest-watch`. It will automatically check the unit test code coverage when files get changed.
- (Optional) If using VS Code, then install [Coverage Gutters](https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters) and run `Coverage Gutters: Watch`. It will read the auto-updated `lcov.info` file and update the coverage lines accordingly.

### Debugging UI setup (remote)
- Follow https://github.com/Hanabi-Live/hanabi-live/blob/main/docs/install.md#installation-for-developmentproduction-linux.
- Change `.env` with the server public IP address.
- Backup: `pg_dump -U hanabiuser -d hanabi -f backup.sql`
- Restore: `psql -U hanabiuser -d hanabi < backup.sql`

#### Postgres Trouble shooting
- We might need to change `pg_hda.conf` by replacing `peer` with `md5` for `local` users group (for 'hanabiuser').
  ```sh
  sudo vim /etc/postgresql/16/main/pg_hba.conf
  sudo systemctl restart postgresql
  ```
