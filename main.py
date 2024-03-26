import re
import sys
import json
from requests import get
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt
import discord
from discord.ext import commands
from datatypes import *
from exceptions import *
from bot_token import BOT_TOKEN
from nsfw_utils import *
from constants import *


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


def create_bargraph_image(kvp, name):
    # Extract keys and values from the dictionary
    labels = list(kvp.keys())
    values = list(kvp.values())

    # Create a bar graph with value annotations
    fig, ax = plt.subplots()
    bars = ax.bar(labels, values, color="green")
    bars[-1].set_color("red")

    ax.set_xlabel("Guesses to Solve")
    ax.set_ylabel("Number of Wordles")
    ax.set_title(f"Guesses Distribution for {name}")

    # Add value annotations to the bars
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval, round(yval, 2), ha="center", va="bottom")

    # Save the plot to a BytesIO object
    image_stream = BytesIO()
    plt.savefig(image_stream, format="png")
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
    print("Compiling Wordle regex pattern...")
    wordle_pattern = re.compile(r'.*Wordle\s+\d+\s+[1-6X]/6\*?.*', re.DOTALL)
    print("Done.")
    print("Reading WordleStats database...")
    database = json.load(open(dbpath))
    print("Done.")
    print("Loading NSFW paths...")
    porn_paths = load_nsfw_paths_and_ctimes(NSFW_SOURCE_PATH)
    print("Done.")

    async def on_ready(self):
        print("Online!")

    async def evaluate_wordle(self, msg, show_feedback=False):
        lines = msg.content.split("\n")
        delete_frontitems_until_regexmatch(lines, r'.*Wordle\s+\d+\s+[1-6X]/6\*?.*')
        delete_rearitems_until_regexmatch(lines, r'^[\U0001F7E9⬛\U0001F7E8].*')
        extract_attempts = lines[0].replace(",", "").replace("🎉", "")
        extract_wordle_day = lines[0].replace(",", "").replace("🎉", "")
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
            await msg.channel.send(f"Error: Malformed input.\n"
                                   f"{e}")
            return

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)
        if self.wordle_pattern.match(msg.content):
            await self.evaluate_wordle(msg, show_feedback=True)
        if "sleepy" in msg.content.lower():
            await msg.channel.send("sleepy mentioned")

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


@bot.command()
@commands.has_permissions(administrator=True)
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
                        # The third square "⬛" may look green in PyCharm.
                        # It actually is the "Black Large Square" emoji, U+2B1B.
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
    def format_top_3(member: NameAndAvg):
        return f"`{member.avgstr()}` - **{member.namestr()}** ({member.fracstr()})"

    def format_other(member: NameAndAvg):
        return f"`{member.avgstr()}` - {member.namestr()} ({member.fracstr()})"
    ret: list[NameAndAvg] = []
    retstr = ""
    for k, v in bot.database["guilds"][str(ctx.guild.id)]["members"].items():
        total_days = len(v.items())
        unsolved = 0
        if total_days < gate or total_days == 0:
            continue
        total_attempts = 0
        for daynumber, details in v.items():
            if not details["solved"]:
                unsolved += 1
                continue
            total_attempts += len(details["attempts"])
        average = total_attempts / (total_days - unsolved)
        user = await bot.fetch_user(int(k))
        ret.append(NameAndAvg(user.name, average, total_days, unsolved))
    if not ret:
        await ctx.send(f"No members have played played enough Wordle to be on the leaderboards.\n"
                       f"The leaderboard gate is {gate} plays.")
        return
    ret.sort(key=lambda x: x.average)
    for idx, pair in enumerate(ret):
        if idx == 0:
            retstr += f"🥇: {format_top_3(pair)}\n"
        elif idx == 1:
            retstr += f"🥈: {format_top_3(pair)}\n"
        elif idx == 2:
            retstr += f"🥉: {format_top_3(pair)}\n"
        else:
            retstr += f"`#{idx + 1}`: {format_other(pair)}\n"
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
        if not v["solved"]:
            data["X"] += 1
        else:
            data[str(len(v["attempts"]))] += 1
    user = await bot.fetch_user(member_id)
    graph_raw = create_bargraph_image(data, user.name)
    await ctx.send(file=discord.File(graph_raw, f"dist_{ctx.guild.id}_{member_id}.png"))
    del graph_raw  # Free memory


@bot.command(aliases=["rm"])
@commands.has_permissions(administrator=True)
async def remove(ctx, member_id, day):
    if str(member_id) not in bot.database["guilds"][str(ctx.guild.id)]["members"]:
        await ctx.send(f"Member with ID {member_id} not found!")
        return
    if str(day) not in bot.database["guilds"][str(ctx.guild.id)]["members"][str(member_id)]:
        await ctx.send(f"Member ID {member_id} has no entry for {day}!")
        return
    try:
        bot.database["guilds"][str(ctx.guild.id)]["members"][str(member_id)].pop(str(day))
        with open(dbpath, 'w') as updated:
            json.dump(bot.database, updated, indent=2)
        user = await bot.fetch_user(member_id)
        await ctx.send(f"Deleted Day {day} for user {user.name}.")
    except Exception as e:
        await ctx.send(e)


@bot.command(aliases=["refreshporn"])
@commands.is_nsfw()
async def update_catalog(ctx):
    bot.porn_paths = load_nsfw_paths_and_ctimes(NSFW_SOURCE_PATH)
    await ctx.send("Refreshed porn catalog!")


@bot.command()
@commands.is_nsfw()
async def porn(ctx):
    try:
        imagepath = choose_image(bot.porn_paths, False, 0)
        ext = imagepath.split(".")[-1]
        await ctx.send(file=discord.File(imagepath, f"hereyougo_youhornybastard.{ext}"))
    except discord.errors.HTTPException as e:
        await ctx.send(e)


@bot.command()
@commands.is_nsfw()
async def newporn(ctx, newest_count=100):
    try:
        imagepath = choose_image(bot.porn_paths, True, newest_count)
        ext = imagepath.split(".")[-1]
        await ctx.send(file=discord.File(imagepath, f"hereyougo_youhornybastard.{ext}"))
    except discord.errors.HTTPException as e:
        await ctx.send(e)


@bot.command()
@commands.is_nsfw()
async def porngif(ctx):
    try:
        imagepath = choose_image(bot.porn_paths, False, 0, "gif")
        ext = imagepath.split(".")[-1]
        await ctx.send(file=discord.File(imagepath, f"hereyougo_youhornybastard.{ext}"))
    except discord.errors.HTTPException as e:
        await ctx.send(e)


@bot.command(aliases=["json"])
async def give_json(ctx):
    json_string = json.dumps(bot.database["guilds"][str(ctx.guild.id)]["members"][str(ctx.author.id)], indent=2)
    username = await bot.fetch_user(ctx.author.id)
    guildname = await bot.fetch_guild(ctx.guild.id)
    filename = f"{username}-{guildname}-wordles.json"
    json_to_send = BytesIO(json_string.encode())
    await ctx.send(file=discord.File(json_to_send, filename=filename))


@bot.command(aliases=["pfp"])
async def profilepic(ctx, scope="server", member=None):
    if scope not in ["server", "global"]:
        await ctx.send("Specify either server or global.")
        return
    user_id = member or ctx.author.id
    user = await bot.fetch_user(user_id)
    if scope == "server":
        avatar = BytesIO(get(user.display_avatar.url).content)
    else:
        avatar = BytesIO(get(user.avatar.url).content)
    ext = user.avatar.url.split(".")[-1].split("?")[0]
    await ctx.send(f"{user.name}'s avatar:", file=discord.File(avatar, filename=f"{user_id}.{ext}"))


bot.run(BOT_TOKEN)
