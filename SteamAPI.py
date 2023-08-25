import requests

class SteamAPI:
	def __init__(self, api_key):
		self.api_key = api_key

	def get_userid64(self, user):
		params = {
			"key": self.api_key,
			"vanityurl": user
		}
		response = requests.get("http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/", params=params)
		if response.status_code == 200 and "steamid" in response.text:
			return response.json()["response"]["steamid"]
		return None

	def get_player_profile(self, id64):
		params = {
			"key": self.api_key,
			"steamids": id64
		}
		response = requests.get("https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/", params=params)
		if not response.ok or len(response.json()["response"]["players"]) < 1:
			return None

		pinfo = response.json()["response"]["players"][0]
		return SteamProfile(pinfo["personaname"], pinfo["avatarfull"], pinfo["profileurl"], pinfo["loccountrycode"] if "loccountrycode" in pinfo else None, pinfo["timecreated"] if "timecreated" in pinfo else None)

	def get_player_bans(self, id64):
		params = {
			"key": self.api_key,
			"steamids": id64
		}
		response = requests.get("https://api.steampowered.com/ISteamUser/GetPlayerBans/v1/", params=params)
		if not response.ok:
			return None

		bans = SteamBans(0, 0, False)
		players = response.json()["players"]
		if len(players) == 0: return bans
		pbans = players[0]
		if "NumberOfVACBans" in response.text: bans.vac_bans = pbans["NumberOfVACBans"]
		if "NumberOfGameBans" in response.text: bans.game_bans = pbans["NumberOfGameBans"]
		if "EconomyBan" in response.text: bans.trade_ban = pbans["EconomyBan"] != "none"
		return bans

	def get_level(self, id64):
		params = {
			"key": self.api_key,
			"steamid": id64
		}
		response = requests.get("http://api.steampowered.com/IPlayerService/GetBadges/v1/", params=params)
		if not response.ok:
			return -1

		json = response.json()
		if "response" not in json or "player_level" not in json["response"]:
			return -1
			
		return json["response"]["player_level"]

class SteamProfile:
	def __init__(self, name, avatar, url, country, creation_time):
		self.name = name
		self.avatar = avatar
		self.url = url
		self.country = country
		self.creation_time = creation_time

class SteamBans:
	def __init__(self, vac, game, trade):
		self.vac_bans = vac
		self.game_bans = game 
		self.trade_ban = trade