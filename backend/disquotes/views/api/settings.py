from flask import g
from flask_restplus import Namespace, abort, fields
from sqlalchemy import or_

from disquotes.model import Channel, Setting, Server
from disquotes.views.api.base import ResourceBase

ns = Namespace("settings", "Settings storage.")

settings_model = ns.model("SettingsModel", {
    "settings": fields.Raw
})


@ns.route("/<int:server>")
@ns.doc(params={"server": "Discord Server ID"})
class SettingsResource(ResourceBase):
    @ns.marshal_with(settings_model)
    def get(self, server):
        settings = self.get_settings(server)

        return {
            "settings": settings.store
        }

    @ns.param("key", "Setting key", _in="formData", required=True)
    @ns.param("value", "Setting value", _in="formData", required=True)
    def put(self, server):
        settings = self.get_settings(server)

        key = self.get_field("key")
        value = str(self.get_field("value"))

        settings.store[key] = value

    @ns.param("key", "Settings key", _in="formData", required=True)
    def delete(self, server):
        settings = self.get_settings(server)
        try:
            del settings.store[self.get_field("key")]
        except KeyError:
            pass

    def get_settings(self, server):
        server, _ = self.get_server_channel(server=server, create=True)

        settings = g.db.query(Setting).filter(Setting.server_id == server.id).scalar()
        if not settings:
            settings = Setting(
                server_id=server.id,
                store={}
            )
            g.db.add(settings)
            g.db.commit()

        return settings
