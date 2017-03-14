# coding=utf-8
import operator

from homura import NepeatBot

bot = NepeatBot()

print("""---
layout: page
title: Permissions
categories: Help
description: This is a list of all the commands with their permissions.
---
""")

def mdescape(unescaped):
    return unescaped.replace("|", "\|").replace("<", "\<").replace(">", "\>")

for plugin in bot.plugins:
    if plugin.owner_only:
        continue

    print("## " + plugin.__class__.__name__.replace("Plugin", ""))

    commands = {}
    for func in plugin.commands.values():
        commands[func.info["name"]] = func.info.get("permission", "<h1>PERMISSION MISSING</h1>")


    for name, perm in sorted(commands.items(), key=operator.itemgetter(1)):
        name = mdescape(name)
        print(f'**{name}** - {perm}\n')
