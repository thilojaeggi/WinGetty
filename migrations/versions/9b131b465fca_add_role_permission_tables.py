"""Add role, permission tables

Revision ID: 9b131b465fca
Revises: 294fa8c8c153
Create Date: 2023-07-04 21:45:46.111370

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b131b465fca'
down_revision = '294fa8c8c153'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('permission',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permission')),
    sa.UniqueConstraint('name', name=op.f('uq_permission_name'))
    )
    op.create_table('role',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_role')),
    sa.UniqueConstraint('name', name=op.f('uq_role_name'))
    )
    op.create_table('roles_permissions',
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('permission_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permission.id'], name=op.f('fk_roles_permissions_permission_id_permission')),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], name=op.f('fk_roles_permissions_role_id_role')),
    sa.PrimaryKeyConstraint('role_id', 'permission_id', name=op.f('pk_roles_permissions'))
    )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_user_role_id_role'), 'role', ['role_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_user_role_id_role'), type_='foreignkey')
        batch_op.drop_column('role_id')

    op.drop_table('roles_permissions')
    op.drop_table('role')
    op.drop_table('permission')
    # ### end Alembic commands ###
