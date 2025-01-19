"""Enhance project model for multi-tenancy."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_enhance_project_multitenancy'
down_revision = '001_initial'  # Adjust based on your previous migration
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade database schema."""
    # Add new columns to projects table
    op.add_column('projects', sa.Column('database_shard', sa.String(), nullable=False, server_default='default'))
    op.add_column('projects', sa.Column('redis_namespace', sa.String(), nullable=False, server_default='default'))
    op.add_column('projects', sa.Column('k8s_namespace', sa.String(), nullable=False, server_default='default'))
    op.add_column('projects', sa.Column('agent_config', postgresql.JSON(), nullable=False, server_default='{}'))
    op.add_column('projects', sa.Column('resource_limits', postgresql.JSON(), nullable=False, server_default='{}'))

def downgrade():
    """Downgrade database schema."""
    op.drop_column('projects', 'resource_limits')
    op.drop_column('projects', 'agent_config')
    op.drop_column('projects', 'k8s_namespace')
    op.drop_column('projects', 'redis_namespace')
    op.drop_column('projects', 'database_shard') 