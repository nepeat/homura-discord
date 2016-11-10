from nepeatbot.commands import command

@command("undelete")
async def cmd_undelete(self, message):
    messages = await self.get_events("delete", message.server, message.channel)
    if not messages:
        return await self.send_message(message.channel, "None")

    output = "\n".join(["__{sender}__ - {message}".format(
        sender=deleted["sender"]["display_name"],
        message=deleted["message"]
    ) for deleted in messages])

    await self.send_message(message.channel, output)
