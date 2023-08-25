from config import *
from csgo.client import CSGOClient
from csgo.enums import ECsgoGCMsg
from discord import app_commands
from discord import Webhook
from maps import *
from steam.client import SteamClient
from steam.client.builtins.friends import SteamFriendlist
from steam.client.user import SteamUser
from steam.steamid import SteamID
from SteamAPI import *
import aiohttp
import asyncio
import csgo
import database
import datetime
import discord
import Helpers
import inspect
import math
import os 
import platform
import time

discord_intents = discord.Intents.default()
discord_client = discord.Client(intents=discord_intents)
discord_client.sync_tree = DISCORD_SYNC_TREE
command_tree = app_commands.CommandTree(discord_client)
bot_owner = None

steam_client = SteamClient()
csgo_client = CSGOClient(steam_client)
friendslist = SteamFriendlist(steam_client)
steam_api = SteamAPI(STEAM_API_KEY)
friendslist.messaged = []

db = database.Database(DATABASE_FILE)

def log(text):
	previous_frame = inspect.currentframe().f_back
	(filename, line_number, function_name, lines, index) = inspect.getframeinfo(previous_frame)
	logline = f"{datetime.datetime.now()} {function_name}: {text}"

	print(logline)
	with open(LOG_FILE, "a") as file:
		file.write(f"{logline}\n")

def get_player_profile(id64):
	inspect_params = { "account_id": SteamID(id64).as_32, "request_level": 32 }
	csgo_client.send(ECsgoGCMsg.EMsgGCCStrike15_v2_ClientRequestPlayersProfile, inspect_params)
	response = csgo_client.wait_event(ECsgoGCMsg.EMsgGCCStrike15_v2_PlayersProfile, timeout=3)
	return None if response is None else response[0].account_profiles[0]

def remove_url_parts(user):
	remove_from_user = [ "https://steamcommunity.com/id/", "https://steamcommunity.com/profiles/", "/" ]
	for to_remove in remove_from_user: user = user.replace(to_remove, "")
	return user

def steam_login():
	steam_client.set_credential_location("credentials")

	if steam_client.logged_on: return

	if steam_client.relogin_available: steam_client.relogin()
	elif steam_client.login_key is not None: steam_client.login(username=STEAM_USERNAME, login_key=steam_client.login_key)
	else: steam_client.cli_login(username=STEAM_USERNAME, password=STEAM_PASSWORD)

@steam_client.on("logged_on")
def steam_logged_on():
	log(f"Logged in as {steam_client.user.steam_id} ({steam_client.user.name})")

@steam_client.on("chat_message")
def steam_chat_message(user, message):
	if user.steam_id not in friendslist.messaged:
		user.send_message(f"Hey, {user.name}! This is a bot account. No-one will read these messages.")
		return
	friendslist.messaged.append(user.steam_id)

@friendslist.on("friend_invite")
def fl_friend_invite(user):
	log(f"New friend request from {user.steam_id} ({user.name}), adding...")
	friendslist.add(user)

async def steam_idle():
	while True:
		steam_client.idle()
		await asyncio.sleep(.1)

async def fetch_owner():
	global bot_owner
	while True:
		application_info = await discord_client.application_info()
		bot_owner = application_info.owner
		await asyncio.sleep(600)

@discord_client.event
async def on_ready():
	discord_client.loop.create_task(steam_idle())
	discord_client.loop.create_task(fetch_owner())
	steam_login()

	if discord_client.sync_tree:
		log(f"Syncing command tree...")
		await command_tree.sync()
		discord_client.sync_tree = False

	await discord_client.change_presence(activity=discord.Game(name="/help"))

	log(f"Ready")

@command_tree.error
async def command_error(interaction, error):
	message = f"An error occurred while executing that command:\n```{error}```\nIf this keeps happening you can join the [Discord server]({DISCORD_SERVER_INVITE}) and ask for help."
	await interaction.followup.send(message)

@command_tree.command(description="Gets some info about the bot.")
async def info(interaction):
	embed=discord.Embed(
		title="Bot Info",
		description=f"Bot Owner: @{bot_owner.name}\nServer: {DISCORD_SERVER_INVITE}\nOriginal Source by [Everly](https://kokomi.gay/@everly)",
		color=0xFC0272
	)

	embed.add_field(name="OS", value=f"{platform.system()} {platform.release()}", inline=True)
	embed.add_field(name="Uptime", value=f"Up since <t:{int(start_time)}:f>", inline=True)

	await interaction.response.send_message(embed=embed)

@command_tree.command(description="Get an invite link for the bot.")
async def invite(interaction):
	embed=discord.Embed(
		title="Bot Invite",
		description=f"You can use [this link]({DISCORD_BOT_INVITE}) to add the bot to your server.", 
		color=0xFC0272
	)

	await interaction.response.send_message(embed=embed)

@command_tree.command(description="Shows all the commands.")
async def help(interaction):
	embed=discord.Embed(
		title="Command List",
		description=f"For other help, you can join the [Discord server]({DISCORD_SERVER_INVITE})",
		color=0xFC0272
	)

	for command in command_tree.get_commands(type=discord.AppCommandType.chat_input):
		embed.add_field(name=command.name, value=command.description, inline=False)

	await interaction.response.send_message(embed=embed)

def launch_csgo():
	if csgo_client.connection_status == csgo.enums.GCConnectionStatus.NO_SESSION:
		log("NO_SESSION: Logging in and launching CS:GO again.")
		steam_login()
		csgo_client.launch()

def parse_user(user):
	user = remove_url_parts(user)

	# Check CS:GO friend code first, because this doesn't make a web request
	fc_user = SteamID.from_csgo_friend_code(user)
	if fc_user is None:
		# If the user can't be parsed as friend code or ID64, resolve the vanity URL
		steam_api_user = steam_api.get_userid64(user)
		if steam_api_user is not None:
			user = steam_api_user
		else:
			if not SteamID(user).is_valid():
				return None
	else:
		user = fc_user

	return user

def get_next_wednesday(d):
	# 2 is wednesday
	days_ahead = 2 - d.weekday()
	if days_ahead <= 0:
		days_ahead += 7
	return d + datetime.timedelta(days=days_ahead)

async def send_profile(interaction, target_user, disable_emojis):
	log(f"Requesting profile for `{target_user}`")

	launch_csgo()

	user = parse_user(target_user)
	if not user:
		await interaction.followup.send(f"Unable to parse `{target_user}` as vanity URL, ID64 or CS:GO friend code.")
		return

	steam_profile = steam_api.get_player_profile(user)
	if steam_profile is None:
		await interaction.followup.send(f"Unable to get Steam profile for `{user}`.")
		return

	bans = steam_api.get_player_bans(user)
	if bans is None:
		await interaction.followup.send(f"Unable to get bans for `{user}`.")
		return

	steam_level = steam_api.get_level(user)

	# 5 attempts to get CS:GO profile because CS:GO sometimes just doesn't want to give it first try
	get_profile_tries = 5
	for i in range(get_profile_tries):
		csgo_profile = get_player_profile(user)
		log(f"Requesting CS:GO profile for `{user}`... Try #{i+1}")
		if csgo_profile is not None:
			break

	if csgo_profile is None:
		await interaction.followup.send(f"Unable to get CS:GO profile after {get_profile_tries} tries.")
		return

	# Subtract 327680000 from the XP because CS:GO adds that for whatever cool reason
	# Also set it to 0 if it's under 0 for some reason
	player_xp = max(0, csgo_profile.player_cur_xp - 327680000)

	xp_until_reduced = 11167 # https://counterstrike.fandom.com/wiki/Profile_Rank#XP_Penalty
	xp_per_level = 5000

	# Get account age, country and add some ban info to the description
	time_created = f"<t:{steam_profile.creation_time}:R>" if steam_profile.creation_time else "Unknown"
	description = f"Created: {time_created}"
	if steam_level >= 0:
		description += f"\nSteam Level: {steam_level}"

	country = Helpers.get_country_string(steam_profile.country, disable_emojis)
	if country is not None:
		description += f"\n{country}"
	if bans.vac_bans > 0: description += f"\n**{bans.vac_bans} VAC BAN(S)**"
	if bans.game_bans > 0: description += f"\n**{bans.game_bans} GAME BAN(S)**"
	if bans.trade_ban: description += f"\n**TRANDE BANNED**"

	embed_color = 0xFFFFFF if steam_level < 0 else steam_level_colors[math.floor((steam_level % 100) / 10)]
	embed = discord.Embed(
		title=steam_profile.name,
		url=steam_profile.url,
		description=description,
		color=embed_color
	)

	embed.set_footer(text="Made by Everly - https://kokomi.gay/@everly")

	# Set the requested profile's avatar as the embed thumbnail
	embed.set_thumbnail(url=steam_profile.avatar)

	# Commendations
	embed.add_field(name="Friendly", value=csgo_profile.commendation.cmd_friendly, inline=True)
	embed.add_field(name="Teacher", value=csgo_profile.commendation.cmd_teaching, inline=True)
	embed.add_field(name="Leader", value=csgo_profile.commendation.cmd_leader, inline=True)

	# Level, XP and friend code
	embed.add_field(name="Level", value=Helpers.get_level_string(csgo_profile.player_level, disable_emojis), inline=True)
	embed.add_field(name="Current XP", value=f"{player_xp} ({math.floor(player_xp / xp_per_level * 100)}%)", inline=True)
	embed.add_field(name="Friend Code", value=SteamID(user).as_csgo_friend_code, inline=True)

	# A bunch of stuff to make ranks look good
	if csgo_profile.ranking.account_id == 0:
		embed.add_field(name="Rank", value=f"can't get rank info (do you have [the bot]({SteamID(steam_client.user.steam_id).community_url}) added on steam?)", inline=False)
	else:
		# 'Blank' emoji (fully transparent)
		filler_emoji = "<:filler:998563551700602981>"

		competitive_rank = Helpers.RankInfo(ranks_short_map, ranks_emojis_map, csgo_profile.ranking.rank_id, csgo_profile.ranking.wins)
		embed.add_field(name="Competitive Rank", value=f"{competitive_rank.get_rank_string(disable_emojis)}\n{competitive_rank.get_wins_string(filler_emoji, disable_emojis)}", inline=True)

		wingman_rank = Helpers.RankInfo(wingman_ranks_short_map, wingman_ranks_emojis_map, 0, 0)
		dangerzone_rank = Helpers.RankInfo(dangerzone_ranks_short_map, dangerzone_ranks_emojis_map, 0, 0)
		if len(csgo_profile.rankings) >= 2:
			wingman_rank.set_id(csgo_profile.rankings[0].rank_id)
			wingman_rank.set_wins(csgo_profile.rankings[0].wins)
			dangerzone_rank.set_id(csgo_profile.rankings[1].rank_id)
			dangerzone_rank.set_wins(csgo_profile.rankings[1].wins)

		embed.add_field(name="Wingman Rank", value=f"{wingman_rank.get_rank_string(disable_emojis)}\n{wingman_rank.get_wins_string(filler_emoji, disable_emojis)}", inline=True)
		embed.add_field(name="Dangerzone Rank", value=f"{dangerzone_rank.get_rank_string(disable_emojis)}\n{dangerzone_rank.get_wins_string(filler_emoji, disable_emojis)}", inline=True)

	# Add all medals to embed, but seperate them in different fields so they don't go over the 1024 character limit
	medals_text_list = Helpers.get_medals_for_embed(csgo_profile.medals.display_items_defidx, 1000, disable_emojis)
	if medals_text_list[0] != "":
		pages = math.ceil(len(csgo_profile.medals.display_items_defidx) / 5)
		embed.add_field(name=f"Medals ({pages} page{'s' if pages > 1 else ''})", value=medals_text_list[0], inline=True)
		for medals_text in medals_text_list[1:]:
			embed.add_field(name="\u200b", value=medals_text, inline=True)

	await interaction.followup.send(embed=embed)

@command_tree.command(description="Get someone's CS:GO profile")
@app_commands.describe(target_user="Users ID64/custom URL/CS:GO friend code")
async def profile(interaction, target_user: str, disable_emojis: bool = DISABLE_EMOJIS_DEFAULT):
	await interaction.response.defer()
	await send_profile(interaction, target_user, disable_emojis)

@command_tree.command(description="Get your default Steam profile")
async def myprofile(interaction, disable_emojis: bool = DISABLE_EMOJIS_DEFAULT):
	await interaction.response.defer()

	steam_id = db.get_default_profile(interaction.user.id)
	if not steam_id:
		await interaction.followup.send(f"Couldn't find your default profile. Did you set it with `/setdefaultprofile`?")
		return

	await send_profile(interaction, str(steam_id), disable_emojis)

@command_tree.command(description="Set a Steam profile as your default")
@app_commands.describe(target_user="ID64/custom URL/CS:GO friend code to set as default")
async def setdefaultprofile(interaction, target_user: str):
	await interaction.response.defer()

	user = parse_user(target_user)
	if not user:
		await interaction.followup.send(f"Unable to parse `{target_user}` as vanity URL, ID64 or CS:GO friend code.")
		return

	db.set_default_profile(interaction.user.id, user)

	await interaction.followup.send(f"Set `{user}` as your default profile.")

@command_tree.command(description="Remove your default Steam profile")
async def removedefaultprofile(interaction):
	await interaction.response.defer()
	db.remove_default_profile(interaction.user.id)
	await interaction.followup.send(f"Removed your default profile.")

if __name__ == "__main__":
	start_time = time.time()
	discord_client.run(DISCORD_TOKEN)