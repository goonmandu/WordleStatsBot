import discord
from bot_token import BOT_TOKEN
import re
import json
from exceptions import *
import os
from discord.ext import commands

# Create JSON file if it does not exist
dbpath = "./database.json"
if not os.path.exists(dbpath):
    with open(dbpath, "w+") as f:
        f.seek(0)
        f.write('{\n'
                '\t"guilds": {\n'
                '\t}\n'
                '}')

# Test whether JSON file is valid
try:
    with open(dbpath, 'r') as jsondb:
        json.load(jsondb)
except json.JSONDecodeError as e:
    print(f"Invalid JSON file:\n"
          f"{e}")
except Exception as e:
    print(f"Something went wrong:\n"
          f"{e}")


class WordleTracker(commands.Bot):
    wordle_pattern = re.compile(r'^Wordle\s+\d+\s+[1-6X]/6\*?.*', re.DOTALL)
    database = json.load(open(dbpath))

    async def on_ready(self):
        print("Online!")

    async def evaluate_wordle(self, msg):
        lines = msg.content.split("\n")
        extract_attempts = lines[0]
        extract_wordle_day = lines[0]
        try:
            wordle_day = re.sub("\s+[1-6X]/6\*?.*", "", re.sub("Wordle\s+", "", extract_wordle_day))
            attempts = re.sub("/6\*?.*", "", re.sub("Wordle\s+\d+\s+", "", extract_attempts))
            attempts_int = 6 if attempts == "X" else int(attempts)
            guildid = str(msg.guild.id)
            authorid = str(msg.author.id)
            count = [[0, 0, 0, 0, 0] for _ in range(6 if attempts == "X" else int(attempts))]
            if attempts_int != len(lines) - 2:
                raise NumberOfAttemptsMismatchException(int(attempts), len(lines) - 2)
            for idx, line in enumerate(lines[2:]):
                for ltridx, ltr in enumerate(line):
                    if ltr == "🟩":
                        count[idx][ltridx] = 2
                    if ltr == "🟨":
                        count[idx][ltridx] = 1
            full_stats = {"day": wordle_day, "attempts": count, "solved": attempts != "X", "hard": "*" in lines[0]}
            if guildid not in self.database["guilds"]:
                self.database["guilds"][guildid] = {"members": {}}
            if authorid not in self.database["guilds"][guildid]["members"]:
                self.database["guilds"][str(msg.guild.id)]["members"][authorid] = {}
            self.database["guilds"][guildid]["members"][authorid][wordle_day] = full_stats
            with open(dbpath, 'w') as updated:
                json.dump(self.database, updated, indent=2)
            await msg.channel.send(f"Data recorded: Day {wordle_day} for user <@{msg.author.id}>.")

        except Exception as e:
            await msg.channel.send(f"Error: Malformed input.\n"
                                   f"{e}")
            return

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)
        if self.wordle_pattern.match(msg.content):
            await self.evaluate_wordle(msg)

    async def on_disconnect(self):
        print("Offline!")


intents = discord.Intents.default()
intents.message_content = True

bot = WordleTracker(intents=intents, command_prefix="wd!")

@bot.command()
async def stats(ctx, *, day_number=None):
    userdata = bot.database["guilds"][str(ctx.guild.id)]["members"][str(ctx.author.id)]
    ret = ""
    if day_number is None:
        for idx, daydata in enumerate(userdata.values()):
            ret += f"Wordle {daydata['day']} {len(daydata['attempts']) if daydata['solved'] else 'X'}/6" \
                   f"{'*' if daydata['hard'] else ''}\n\n"
            for entry in daydata["attempts"]:
                ret += f"`{entry}`\n"
            ret += "\n\n"
        ret += "\n\n"
    else:
        daydata = userdata[day_number]
        ret += f"Wordle {daydata['day']} {len(daydata['attempts']) if daydata['solved'] else 'X'}/6" \
               f"{'*' if daydata['hard'] else ''}\n\n"
        for entry in daydata["attempts"]:
            ret += f"`{entry}`\n"
    await ctx.send(ret)

bot.run(BOT_TOKEN)
