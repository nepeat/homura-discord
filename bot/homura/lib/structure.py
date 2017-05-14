# coding=utf-8
class BackendError(Exception):
    pass


class CommandError(Exception):
    pass


class Message(object):
    def __init__(self, content=None, embed=None, reply=False, delete_after=0, delete_invoking=0):
        self.content = content
        self.embed = embed
        self.reply = reply
        self.delete_after = delete_after
        self.delete_invoking = delete_invoking