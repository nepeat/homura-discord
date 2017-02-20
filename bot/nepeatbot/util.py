import re
from urllib.parse import urlencode

import aiohttp


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


def validate_regex(regex):
    try:
        re.compile(regex)
        return True
    except re.error:
        return False
