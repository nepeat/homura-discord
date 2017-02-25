# Base exception class for music

class MusicException(Exception):
    def __init__(self, message, *, expire_in=0):
        self._message = message
        self.expire_in = expire_in

    @property
    def message(self):
        return self._message


# Something went wrong during the processing of a song/ytdl stuff

class ExtractionError(MusicException):
    pass


# The no processing entry type failed and an entry was a playlist/vice versa

class WrongEntryTypeError(MusicException):
    def __init__(self, message, is_playlist, use_url):
        super().__init__(message)
        self.is_playlist = is_playlist
        self.use_url = use_url
