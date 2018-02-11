"""messages table

Revision ID: 588d317c3eac
Revises: 2bd6644d74cd
Create Date: 2018-02-11 00:59:22.546800

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '588d317c3eac'
down_revision = '2bd6644d74cd'
branch_labels = None
depends_on = None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.BigInteger(), nullable=False),
    sa.Column('server_id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.BigInteger(), nullable=False),
    sa.Column('pinned', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('message', sa.Unicode(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ),
    sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('message_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('messages')
    # ### end Alembic commands ###
