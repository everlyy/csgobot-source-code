from maps import *

class Medal:
	def __init__(self, id, name, prefix):
		self.id = id 
		self.name = name 
		self.prefix = prefix

	def get_medal_from_id(medal_id):
		if medal_id not in medal_id_map:
			return Medal(medal_id, "Unknown medal", f"`{medal_id}`")

		prefix = "❓" if medal_id not in medal_emoji_map else medal_emoji_map[medal_id]
		return Medal(medal_id, medal_id_map[medal_id], prefix)

def get_medals_for_embed(medal_ids, character_limit, disable_emojis):
	medals_text_split = [""]
	index = 0
	for medal_id in medal_ids:
		medal = Medal.get_medal_from_id(medal_id)

		if disable_emojis:
			medal_text = f"{medal.name}\n"
		else:
			medal_text = f"{medal.prefix} {medal.name}\n"

		if len(medals_text_split[index]) + len(medal_text) > character_limit:
			index += 1
			medals_text_split.append("")
		medals_text_split[index] += medal_text

	return medals_text_split

class RankInfo:
	def __init__(self, rank_map, emoji_map, rank_id, wins):
		self.map = rank_map
		self.emoji_map = emoji_map
		self.id = rank_id
		self.name = self.map[self.id]
		self.max = len(self.map) - 1
		self.emoji = self.emoji_map[self.id]
		self.wins = wins

	def set_id(self, new_id):
		self.name = self.map[new_id]
		self.emoji = self.emoji_map[new_id]
		self.id = new_id

	def set_wins(self, new_wins):
		self.wins = new_wins

	def get_rank_string(self, disable_emojis):
		if disable_emojis:
			return f"{self.name} ({self.id}/{self.max})"
		else:
			return f"{self.emoji} {self.name} ({self.id}/{self.max})"

	def get_wins_string(self, filler_emoji, disable_emojis):
		filler = "" if (self.id == 0 or disable_emojis) else f"{filler_emoji}{filler_emoji} "
		return f"{filler}{self.wins} wins"

def get_level_string(level, disable_emojis):
	if disable_emojis:
		return f"{levels_map[level]} Rank {level}"
	else:
		return f"{levels_emojis_map[level]} {levels_map[level]} Rank {level}"

def get_country_string(country_code, disable_emojis):
	if disable_emojis:
		return None if country_code is None else country_codes_map[country_code.upper()]
	else:
		return None if country_code is None else f":flag_{country_code.lower()}: {country_codes_map[country_code.upper()]}"