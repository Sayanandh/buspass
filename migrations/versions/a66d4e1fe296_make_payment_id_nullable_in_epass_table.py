"""Make payment_id nullable in epass table

Revision ID: a66d4e1fe296
Revises: 03ddd2fa52b8
Create Date: 2025-03-23 21:49:55.989094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a66d4e1fe296'
down_revision = '03ddd2fa52b8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('epass', schema=None) as batch_op:
        batch_op.alter_column('payment_id',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('epass', schema=None) as batch_op:
        batch_op.alter_column('payment_id',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)

    # ### end Alembic commands ###
