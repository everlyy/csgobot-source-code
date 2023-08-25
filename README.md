# Everly's CS:GO Bot

Code is very whacky don't judge me. \
I also didn't spend time on making the run instructions properly, so just use your brain for a second and you'll get through it.

# How to run

This won't be easy to just set up and run, because I never intended it to be used by anyone else but me.

If you want emojis to work you have to get all the images for ranks, medals, pins and all the other things. You can get them from `pak01_dir.vpk` in CS:GO's game folder, it's up to you to extract the images and put them in Discord servers for the bot to use. Then you have to edit all the emoji IDs in `maps.py` to the IDs of the emojis you have. You can get an emoji's ID by puttin a backslash (`\`) in front of an emoji and sending it.

 1. Install `steam[client]`, `csgo` and `discord` from pip, you might also have to install `sqlite3`, I don't know if that's something you have to install anymore
 2. Rename `config.def.py` to `config.py` and fill all the empty variables.
 3. Create a folder called `credentials`, this is where your Steam login will be saved
 4. Run `python3 csgobot.py` (Or whatever python is called on your system)
