import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timedelta

# Bot token (replace with your actual token)
TOKEN = "your-bot-token-here"

# Define roles and settings
GIVEAWAY_ROLE_ID_AIMXPERT = 2358456447176671378  # Admin role ID
PARTICIPATION_ROLE_ID_AIMXPERT = [
    2358456447176671376, 2358456447176671375, 2393906006241312798, 2418958228360531990, 2358456447176671378
]  # Roles allowed to participate in the giveaway
GIVEAWAY_ROLE = "Giveaway Winner"  # Role to assign to giveaway winners

# Set up bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True  # Make sure the bot can listen for reactions

bot = commands.Bot(command_prefix="!", intents=intents)

# Store active giveaways
giveaways = {}

# Function to parse time
def parse_duration(duration_str):
    """Parse the duration string and return a timedelta object."""
    if duration_str.endswith("s"):  # Seconds
        return timedelta(seconds=int(duration_str[:-1]))
    elif duration_str.endswith("m"):  # Minutes
        return timedelta(minutes=int(duration_str[:-1]))
    elif duration_str.endswith("h"):  # Hours
        return timedelta(hours=int(duration_str[:-1]))
    elif duration_str.endswith("d"):  # Days
        return timedelta(days=int(duration_str[:-1]))
    else:
        raise ValueError("Invalid duration format. Use s, m, h, or d.")

# Admin giveaway command
@bot.command()
@commands.has_role(GIVEAWAY_ROLE_ID_AIMXPERT)
async def giveaway(ctx, time: str, winners: int, *prizes):
    """
    Admin command to start a giveaway.
    Time format: <number><s/m/h/d> (e.g., 30s, 2m, 1h, 1d)
    Winners is the number of winners.
    Prizes are the giveaway prizes, can be multiple.
    """
    print(f"Received giveaway command with time={time}, winners={winners}, prizes={prizes}")

    if winners <= 0:
        await ctx.send("Number of winners must be a positive number!")
        return

    if len(prizes) == 0:
        await ctx.send("Please provide at least one prize.")
        return

    # Join the prizes into a single string
    prize_str = ' '.join(prizes)

    # Parse the duration and convert it to a timedelta object
    duration = parse_duration(time)
    if not duration:
        await ctx.send("Invalid duration format. Please use s, m, h, or d.")
        return

    # Create giveaway message
    try:
        giveaway_message = await ctx.send(
            f"🎉 **Giveaway started!** 🎉\n"
            f"**Prizes:** {prize_str}\n"
            f"**Duration:** {str(duration)}\n"
            f"React with 🎉 to participate!\n\n"
            f"🔔 **Hurry up! Don't miss your chance!** 🔔"
        )
    except discord.DiscordException as e:
        print(f"Error sending message: {e}")
        await ctx.send("There was an issue with the giveaway. Please try again later.")
        return

    # Add reaction to the giveaway message
    await giveaway_message.add_reaction("🎉")

    # Store giveaway info
    giveaway_info = {
        "duration": duration,
        "winners": winners,
        "prizes": prizes,
        "message": giveaway_message,
        "start_time": datetime.now(),
        "end_time": datetime.now() + duration,
        "participants": []  # Store participants here
    }
    giveaways[giveaway_message.id] = giveaway_info

    # Start countdown and update message
    await countdown_update(giveaway_message, duration.total_seconds())

    # Wait for the duration of the giveaway
    await asyncio.sleep(duration.total_seconds())

    # Pick winners
    giveaway_info = giveaways[giveaway_message.id]
    participants = giveaway_info["participants"]

    if len(participants) == 0:
        await ctx.send("No participants for this giveaway.")
        return

    winners = random.sample(participants, min(giveaway_info["winners"], len(participants)))

    # Assign winner roles and announce
    for i, winner in enumerate(winners):
        prize = giveaway_info["prizes"][i] if i < len(giveaway_info["prizes"]) else "Mystery Prize"
        await ctx.send(f"🎉 **Congratulations {winner.mention}!** 🎉\n"
                       f"You won **{prize}**! 🎁")
        await winner.send(f"🎉 Congratulations! You won **{prize}** in our giveaway!")
        await winner.add_roles(discord.utils.get(ctx.guild.roles, name=GIVEAWAY_ROLE))

    # Remove the giveaway entry
    del giveaways[giveaway_message.id]

async def countdown_update(giveaway_message, duration):
    """
    Countdown to the end of the giveaway.
    """
    for remaining_time in range(int(duration), 0, -10):
        await giveaway_message.edit(content=f"🎉 **Giveaway in progress!** 🎉\nRemaining time: {remaining_time} seconds\nReact with 🎉 to participate!")
        await asyncio.sleep(10)

# Admin command to list active giveaways
@bot.command()
@commands.has_role(GIVEAWAY_ROLE_ID_AIMXPERT)
async def list_giveaways(ctx):
    """
    Admin command to list all active giveaways.
    """
    if not giveaways:
        await ctx.send("No active giveaways.")
        return

    active_giveaways = "\n".join([f"Giveaway ID: {key} | Prize(s): {', '.join(val['prizes'])} | Ends at: {val['end_time']}" for key, val in giveaways.items()])
    await ctx.send(f"Active giveaways:\n{active_giveaways}")

# Event to handle reaction add (user reacts to the giveaway)
@bot.event
async def on_reaction_add(reaction, user):
    """
    Handles the reaction add event for giveaway participation.
    """
    # Only listen to reactions on giveaway messages
    if reaction.message.id not in giveaways:
        return

    giveaway_info = giveaways[reaction.message.id]

    # Check if the user has the participation role or admin role
    if reaction.emoji == "🎉" and (any(role.id == PARTICIPATION_ROLE_ID_AIMXPERT for role in user.roles) or 
                                  any(role.id == GIVEAWAY_ROLE_ID_AIMXPERT for role in user.roles)):
        if user not in giveaway_info["participants"]:
            giveaway_info["participants"].append(user)
        else:
            print(f"{user} is already in the participant list.")

# Error handler for missing permissions
@giveaway.error
async def giveaway_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"{ctx.author.mention}, you do not have the required role to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide all required arguments: `!giveaway <time> <winners> <prizes>`")

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("Bot is ready!")

# Admin command to clear all messages in a channel
@bot.command()
@commands.has_role(GIVEAWAY_ROLE_ID_AIMXPERT)  # Ensure only admins can use this
async def clear_all(ctx):
    """
    Admin command to clear all messages in the channel.
    """
    try:
        # Purge (delete) the last 100 messages in the channel instantly
        deleted = await ctx.channel.purge(limit=100)

        # Send a confirmation message
        await ctx.send(f"Deleted {len(deleted)} message(s)!", delete_after=5)

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Run the bot
bot.run(TOKEN)
