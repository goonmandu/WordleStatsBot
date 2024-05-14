# WordleStats
Records Wordle results in a Discord server and gives fun stats per member.

# Environment
This codebase assumes you are hosting the bot on Linux.

It might work on Unix (e.g. macOS) but I haven't tested it.

# Key Features
- Automatically recognizes and records Wordle results.
- `!dist` - Distribution graph
- `!lb` - Server leaderboards
- `!json` - All of your results in one JSON file
- `!oldresults` - **Admin only:** Scans given channels and adds existing Wordle results to database
- `!remove` - **Admin only:** Removes a User ID's Wordle entry for a given Day
- Other commands are found in `main.py`, but are insignificant and/or mainly for development purposes.
- 