# youtube-dl plugin loader is nice :)
from nepeatbot.plugins._plugins import *

ALL_PLUGINS = [
    klass
    for name, klass in globals().items()
    if name.endswith("Plugin")
]
