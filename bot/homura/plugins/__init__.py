# youtube-dl plugin loader is nice :)
from homura.plugins._plugins import *  # NOQA

ALL_PLUGINS = [
    klass
    for name, klass in globals().items()
    if name.endswith("Plugin")
]
