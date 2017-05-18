# coding=utf-8
import io
import json
import operator
import os
import sys

import yaml
from homura import NepeatBot

# Argument parsing

try:
    export_type = sys.argv[1]
    if export_type.lower() not in ["json", "yaml"]:
        raise ValueError(f"{export_type} is not a valid extension.")
except IndexError:
    export_type = "json"
except ValueError as e:
    print(str(e))
    sys.exit(os.EX_USAGE)

# Data generation

bot = NepeatBot()


def escape(text):
    return text.replace("|", "\|")


output = {}

for plugin in bot.plugins:
    if plugin.owner_only:
        continue

    plugin_name = plugin.__class__.__name__.replace("Plugin", "")
    if plugin_name not in output:
        output[plugin_name] = {"commands": []}

    for command_name, command_func in sorted(plugin.commands.items()):
        name = command_func.info["name"]
        description = command_func.info["description"]

        output[plugin_name]["commands"].append({
            "name": escape(name),
            "description": escape(description),
            "permission": command_func.info.get("permission")
        })

    # bad
    output[plugin_name]["commands"] = sorted(output[plugin_name]["commands"], key=operator.itemgetter("name"))

# Data output

stdout = io.StringIO()

if export_type == "yaml":
    yaml.dump(output, stdout, indent=4, default_flow_style=False)
else:
    json.dump(output, stdout, indent=4)

stdout.seek(0)
print(stdout.read())
