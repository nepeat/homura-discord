# coding=utf-8
from homura import NepeatBot

bot = NepeatBot()

print("""---
layout: page
title: Commands
categories: Help
description: This is a list of all the commands with their descriptions.
---
""")

def mdescape(unescaped):
    return unescaped.replace("|", "\|").replace("<", "\<").replace(">", "\>")

for plugin in bot.plugins:
    if plugin.owner_only:
        continue

    print("## " + plugin.__class__.__name__.replace("Plugin", ""))
    for command_name, command_func in sorted(plugin.commands.items()):
        name = mdescape(command_func.info["name"])
        description = mdescape(command_func.info["description"])

        print(f'**{name}** - {description}\n')
