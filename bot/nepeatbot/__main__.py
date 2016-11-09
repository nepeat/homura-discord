import os

from nepeatbot import NepeatBot

if __name__ == "__main__":
    bot = NepeatBot()
    token = os.environ.get("DISCORD_TOKEN", None)

    if token:
        bot.run(token)
    else:
        raise Exception("Missing token.")
