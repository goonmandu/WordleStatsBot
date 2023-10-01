import os
import re
import sys
import json
from enum import Enum
from datetime import datetime
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
import discord
from discord.ext import commands
from datatypes import *
from exceptions import *
from bot_token import BOT_TOKEN


# Exit Codes
# Anything thrown under OTHER_ERR should be diagnosed and reported in a future patch.
class ExitCode(Enum):
    INVALID_JSON_FILE = 1
    OTHER_ERR         = 2


def delete_frontitems_until_regexmatch(lst, refilter):
    compiled = re.compile(refilter, re.DOTALL)
    index_to_keep = next((i for i, item in enumerate(lst) if compiled.match(item)), None)

    # If a matching item is found, slice the list from that index
    if index_to_keep is not None:
        del lst[:index_to_keep]
    else:
        # If no matching item is found, clear the entire list
        lst.clear()


def delete_rearitems_until_regexmatch(lst, refilter):
    compiled = re.compile(refilter, re.DOTALL)
    # Iterate from the end of the list
    for i in range(len(lst) - 1, -1, -1):
        if compiled.match(lst[i]):
            break  # Stop when a match is found
        del lst[i]  # Delete the current item


def string_contains_substrs(string, substrs):
    for substr in substrs:
        if substr in string:
            return True
    return False


def create_bargraph_image(kvp):
    # Extract keys and values from the dictionary
    labels = list(kvp.keys())
    values = list(kvp.values())

    # Create a bar graph with value annotations
    fig, ax = plt.subplots()
    bars = ax.bar(labels, values)
    ax.set_xlabel('Categories')
    ax.set_ylabel('Values')
    ax.set_title('Bar Graph')

    # Add value annotations to the bars
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval, round(yval, 2), ha='center', va='bottom')

    # Save the plot to a BytesIO object
    image_stream = BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)

    # Clear the plot for the next use
    plt.clf()

    return image_stream


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
          f"{e}", file=sys.stderr)
    exit(ExitCode.INVALID_JSON_FILE)
except Exception as e:
    print(f"Something went wrong:\n"
          f"{e}", file=sys.stderr)
    exit(ExitCode.OTHER_ERR)


class WordleTracker(commands.Bot):
    wordle_pattern = re.compile(r'.*Wordle\s+\d+\s+[1-6X]/6\*?.*', re.DOTALL)
    database = json.load(open(dbpath))

    async def on_ready(self):
        print("Online!")

    async def evaluate_wordle(self, msg, show_feedback=False):
        lines = msg.content.split("\n")
        delete_frontitems_until_regexmatch(lines, r'.*Wordle\s+\d+\s+[1-6X]/6\*?.*')
        delete_rearitems_until_regexmatch(lines, r'^[\U0001F7E9⬛\U0001F7E8].*')
        extract_attempts = lines[0]
        extract_wordle_day = lines[0]
        try:
            wordle_day = re.sub("\s+[1-6X]/6\*?.*", "", re.sub(".*Wordle\s+", "", extract_wordle_day))
            attempts = re.sub("/6\*?.*", "", re.sub(".*Wordle\s+\d+\s+", "", extract_attempts))
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
            if show_feedback:
                await msg.channel.send(f"Data recorded: Day {wordle_day} for user <@{msg.author.id}>.")

        except Exception as e:
            print(f"Error: Malformed input.\n"
                  f"{e}"
                  f"{msg.content}")
            return

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)
        if self.wordle_pattern.match(msg.content):
            await self.evaluate_wordle(msg, show_feedback=True)

    async def on_disconnect(self):
        print("Offline!")


intents = discord.Intents.default()
intents.message_content = True

bot = WordleTracker(intents=intents, command_prefix="!")


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

'''
@bot.command()
async def fetchold(ctx):
    for channel in ctx.guild.channels:
        print(f"Iterating thru {channel.name}")
        try:
            if isinstance(channel, discord.TextChannel):
                async for message in channel.history():
                    if bot.wordle_pattern.match(message.content):
                        await bot.evaluate_wordle(message, show_feedback=False)
        except discord.errors.Forbidden as fe:
            print(fe)
    await ctx.send("Done")
'''


@bot.command()
async def oldresults(ctx, *args):
    channels_to_check = [bot.get_channel(int(channel_id)) for channel_id in args]
    wordle_creation = datetime.strptime("2021-10-01", "%Y-%m-%d")
    today = datetime.now()
    status_message = await ctx.send("Starting...")
    for channel in channels_to_check:
        try:
            if isinstance(channel, discord.TextChannel):
                latest_date = ""
                await status_message.edit(content=f"Iterating through {channel.name}")
                async for message in channel.history(after=wordle_creation, limit=2**32):
                    if latest_date != message.created_at.strftime('%Y-%m-%d'):
                        latest_date = message.created_at.strftime('%Y-%m-%d')
                        await status_message.edit(content=f"Reading {latest_date}")
                    if bot.wordle_pattern.match(message.content) and not message.author.bot \
                            and string_contains_substrs(message.content, ["🟩", "🟨", "⬛"]):
                        await bot.evaluate_wordle(message, show_feedback=False)
        except discord.errors.Forbidden as fe:
            print(fe)
        except IndexError as ie:
            print(ie)
            if 'message' in locals():
                print(message)
                print(message.content)
    await ctx.send("Done")


@bot.command()
async def wordles(ctx, to_check=None):
    ret = []
    if to_check:
        try:
            member_id = int(to_check)
        except ValueError:
            try:
                member_id = int(to_check.rstrip(">").lstrip("<@"))
            except ValueError:
                await ctx.send("Invalid member ID format! Try again.")
                return
    else:
        member_id = ctx.author.id
    for k, v in bot.database["guilds"][str(ctx.guild.id)]["members"][str(member_id)].items():
        ret.append(f"Day {k}: {len(v['attempts']) if v['solved'] else 'X'}/6{'*' if v['hard'] else ''}\n")
    ret.sort()
    retstr = "".join(ret)
    await ctx.send(retstr)


@bot.command(aliases=["lb"])
async def leaderboards(ctx, gate=10):
    ret = []
    retstr = ""
    for k, v in bot.database["guilds"][str(ctx.guild.id)]["members"].items():
        total_days = len(v.items())
        if total_days < gate:
            continue
        total_attempts = 0
        for daynumber, details in v.items():
            total_attempts += len(details["attempts"])
        average = total_attempts / total_days
        user = await bot.fetch_user(int(k))
        ret.append(NameAndAvg(user.name, average, total_days))
    if not ret:
        await ctx.send(f"No members have played played enough Wordle to be on the leaderboards.\n"
                       f"The leaderboard gate is {gate} plays.")
        return
    ret.sort(key=lambda x: x.average)
    for idx, pair in enumerate(ret):
        retstr += f"`#{idx + 1}`: {str(pair)}\n"
    await ctx.send(retstr)

@bot.command(aliases=["dist"])
async def distribution(ctx, to_check=None):
    if to_check:
        try:
            member_id = int(to_check)
        except ValueError:
            try:
                member_id = int(to_check.rstrip(">").lstrip("<@"))
            except ValueError:
                await ctx.send("Invalid member ID format! Try again.")
                return
    else:
        member_id = ctx.author.id
    data = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "X": 0}
    for k, v in bot.database["guilds"][str(ctx.guild.id)]["members"][str(member_id)].items():
        data[str(len(v["attempts"]))] += 1
    graph_raw = create_bargraph_image(data)
    img = Image.open(graph_raw)
    img.show()


bot.run(BOT_TOKEN)
