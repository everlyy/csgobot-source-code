import sqlite3

class Database:
	def __init__(self, filename):
		self.filename = filename
		self.create_tables()

	def create_tables(self):
		db = self.open_db()
		db.execute("CREATE TABLE IF NOT EXISTS defaultprofiles (discord_id INT PRIMARY KEY NOT NULL, steam_id INT NOT NULL)")
		db.close()

	def open_db(self):
		return sqlite3.connect(self.filename)

	def get_default_profile(self, discord_id):
		db = self.open_db()
		
		cmd = "SELECT steam_id FROM defaultprofiles WHERE discord_id == ?"
		args = (discord_id, )
		
		results = db.execute(cmd, args).fetchall()
		db.close()

		if len(results) != 1:
			return None

		return results[0][0]

	def set_default_profile(self, discord_id, steam_id):
		db = self.open_db()

		cmd = "INSERT OR REPLACE INTO defaultprofiles VALUES (?, ?)"
		args = (discord_id, steam_id)
		db.execute(cmd, args)
		db.commit()

		db.close()

	def remove_default_profile(self, discord_id):
		db = self.open_db()

		cmd = "DELETE FROM defaultprofiles WHERE discord_id = ?"
		args = (discord_id, )
		db.execute(cmd, args)
		db.commit()

		db.close()