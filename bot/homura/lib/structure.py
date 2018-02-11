# coding=utf-8
import io

import discord


class BackendError(Exception):
    pass


class CommandError(Exception):
    pass


class Message(object):
    def __init__(self, content=None, embed=None, reply=False, delete_after=0, delete_invoking=0, file=None):
        if isinstance(content, discord.Embed):
            self.content = None
            self.embed = content
        else:
            self.content = content
            self.embed = embed
        self.reply = reply
        self.delete_after = delete_after
        self.delete_invoking = delete_invoking
        self.file = file

    def __del__(self):
        if self.file:
            self.file.close()

    @classmethod
    def from_file(cls, data, filename: str, *args, **kwargs):
        """
        Initializes a Message object from file data.

        :param data: Bytes, string, or a list of bytes for the file content.
        :param filename: Filename of the file to be sent.
        :return: A Message object with the file and other attributes set.
        """
        new_message = cls(*args, **kwargs)
        new_message.set_file(data, filename)

        return new_message

    def set_file(self, data, filename: str):
        """
        Sets the file attribute in the Message a file.

        :param data: Bytes, string, or a list of bytes for the file content.
        :param filename: Filename of the file to be sent.
        :return: The Message object to chain further sets.
        """
        bytes_object = io.BytesIO()

        if isinstance(data, bytes):
            bytes_object.write(data)
        elif isinstance(data, str):
            bytes_object.write(data.encode("utf8"))
        elif isinstance(data, list):
            try:
                bytes_object.writelines(data)
            except TypeError:
                bytes_object.writelines([_.encode("utf8") for _ in data])

        bytes_object.seek(0)

        self.file = discord.File(
            bytes_object,
            filename=filename
        )

        return self
