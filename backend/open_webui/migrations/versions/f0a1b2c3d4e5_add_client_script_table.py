"""add client_script table

Revision ID: f0a1b2c3d4e5
Revises: 461111b60977
Create Date: 2026-06-15
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = '461111b60977'
branch_labels = None
depends_on = None


def _index_exists(inspector, index_name, table_name):
    """Works for both SQLite and PostgreSQL."""
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'client_script' not in tables:
        op.create_table(
            'client_script',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('is_global', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )

    inspector.clear_cache()
    if 'client_script' in inspector.get_table_names():
        if not _index_exists(inspector, 'client_script_user_id_idx', 'client_script'):
            op.create_index('client_script_user_id_idx', 'client_script', ['user_id'])


def downgrade():
    op.drop_index('client_script_user_id_idx', table_name='client_script')
    op.drop_table('client_script')
