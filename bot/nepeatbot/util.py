import aiohttp
from urllib.parse import urlencode

class Dummy(object):
    def blank_fn(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        return self.blank_fn

    def __setattr__(self, attr, val):
        pass


def sanitize(text: str) -> str:
    text = text.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
    return text
