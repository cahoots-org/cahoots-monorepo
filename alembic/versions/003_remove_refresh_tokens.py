"""Remove refresh_tokens table."""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '003_remove_refresh_tokens'
down_revision = '002_auth_updates'
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade database schema."""
    op.drop_table('refresh_tokens')

def downgrade():
    """Downgrade database schema."""
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('token')
    ) 