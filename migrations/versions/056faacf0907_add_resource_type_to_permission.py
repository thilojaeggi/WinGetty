"""Add resource_type to permission

Revision ID: 056faacf0907
Revises: c993182bb5ec
Create Date: 2024-04-23 20:39:06.379849

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '056faacf0907'
down_revision = 'c993182bb5ec'
branch_labels = None
depends_on = None


def upgrade():
    # Define the enum with proper casing as defined in your Python enum
    resource_type_enum = sa.Enum('Package', 'Version', 'Installer', 'InstallerSwitch', 'User', 'Role', 'Permission', name='resourcetype')
    
    # Apply the enum to the 'permission' table
    with op.batch_alter_table('permission', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resource_type', resource_type_enum, nullable=True))

    # Add resource_id column to 'roles_permissions'
    with op.batch_alter_table('roles_permissions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resource_id', sa.Integer(), nullable=True))

def downgrade():
    # Remove the columns added in the upgrade
    with op.batch_alter_table('roles_permissions', schema=None) as batch_op:
        batch_op.drop_column('resource_id')

    with op.batch_alter_table('permission', schema=None) as batch_op:
        batch_op.drop_column('resource_type')
    
    # Drop the enum type if using PostgreSQL
    op.execute("DROP TYPE resourcetype")
