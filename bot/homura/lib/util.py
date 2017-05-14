# coding=utf-8
import decimal
import hashlib
import re

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


async def get_header(session, url, headerfield=None, *, timeout=5):
    with aiohttp.Timeout(timeout):
        async with session.head(url) as response:
            if headerfield:
                return response.headers.get(headerfield)
            else:
                return response.headers


def md5_file(filename, limit=0):
    fhash = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            fhash.update(chunk)
    return fhash.hexdigest()[-limit:]


def md5_string(string, limit=0):
    try:
        string = string.encode("utf8")
    except AttributeError:
        pass

    fhash = hashlib.md5()
    fhash.update(string)
    return fhash.hexdigest()[-limit:]


def sane_round_int(x):
    return int(decimal.Decimal(x).quantize(1, rounding=decimal.ROUND_HALF_UP))
