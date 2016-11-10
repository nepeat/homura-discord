all_commands = {}


def command(name, dev=False):
    def decorate(f):
        if name in all_commands:
            raise Exception("dev is dumb. (duped command)")

        all_commands[name] = {
            "f": f,
            "dev": dev
        }
        return f
    return decorate

import nepeatbot.commands.moderation
import nepeatbot.commands.quotes
