import asyncio
import functools
import subprocess
from concurrent.futures import ThreadPoolExecutor


class MagickAbstract(object):
    def __init__(self, loop=None):
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.loop = loop

        if not loop:
            self.loop = asyncio.get_event_loop()

    def _magick_image(self, image_data: bytes, args: list=[], magick_module: str="convert"):
        args = ["magick", magick_module] + args

        process = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            input=image_data,
            check=True
        )

        return process.stdout

    async def magick_image(self, *args, **kwargs):
        return await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self._magick_image, *args, **kwargs)
        )

    async def validate(self, image_data: bytes):
        args = [
            "-"
        ]

        return await self.magick_image(image_data, args, "identify")

    async def jpg_compress(self, image_data: bytes, quality: int=5):
        args = [
            "-",
            "-quality",
            str(quality),
            "jpg:-"
        ]

        return await self.magick_image(image_data, args)
