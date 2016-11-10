"""id rename

Revision ID: b12e91c607d7
Revises: 29c2a7faa00b
Create Date: 2016-11-09 20:32:58.866422

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b12e91c607d7'
down_revision = '29c2a7faa00b'
branch_labels = None
depends_on = None

def upgrade():
    fkeys = {
        "servers": {
            "server": "server_id"
        },
        "channels": {
            "channel": "channel_id",
            "server": "server_id"
        },
        "events": {
            "channel": "channel_id",
            "server": "server_id"
        }
    }
    conn = op.get_bind()

    for table, columns in fkeys.items():
        for old, new in columns.items():
            conn.execute("ALTER TABLE {table} RENAME COLUMN {old} TO {new}".format(
                table=table,
                old=old,
                new=new
            ))


def downgrade():
    # please no
    pass
