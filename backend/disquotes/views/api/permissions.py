from flask import g, request
from flask_restplus import Namespace, Resource, abort, fields
from sqlalchemy import or_

from disquotes.model import Channel, Permission, Server
from disquotes.views.api.base import ResourceBase

ns = Namespace("permissions", "Permissions storage.")

permission_model = ns.model("Permission", {
    "permission": fields.String
})

@ns.route("/")
@ns.param("server", "Discord Server ID", type=int, required=True)
@ns.param("channel", "Discord Channel ID", type=int)
class PermissionResource(ResourceBase):
    def get(self):
        server, channel = self.get_server_channel()

        if channel:
            query = g.db.query(Permission.permission).filter(or_(
                Permission.server_id == server.id,
                Permission.channel_id == channel.id
            ))
        else:
            query = g.db.query(Permission.permission).filter(
                Permission.server_id == server.id
            )

        return {
            "permissions": [x[0] for x in query.all()]
        }

    @ns.param("perm", "Permission node", required=True)
    def put(self):
        server, channel = self.get_server_channel(create=True)

        new_perm = Permission(
            server_id=server.id,
            permission=request.args.get("perm")
        )

        if channel:
            new_perm.channel_id = channel.id

        g.db.add(new_perm)

    @ns.param("perm", "Permission node", required=True)
    def delete(self):
        server, channel = self.get_server_channel()

        deleted_perm = g.db.query(Permission).filter(Permission.server_id == server.id)

        if channel:
            deleted_perm = deleted_perm.filter(Permission.channel_id == channel.id)

        deleted_perm = deleted_perm.filter(Permission.permission == request.args.get("perm")).delete()
