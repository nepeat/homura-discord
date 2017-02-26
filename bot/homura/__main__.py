# coding=utf-8
import os

from homura import NepeatBot

if __name__ == "__main__":
    bot = NepeatBot()
    token = os.environ.get("DISCORD_TOKEN", None)

    if token:
        bot.run(token)
    else:
        raise Exception("Missing token.")
