"""add tax_period and findings to audit_cases

Revision ID: a5c1e4d7f823
Revises: 6f7fda7bd1ce
Create Date: 2025-05-08 07:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5c1e4d7f823'
down_revision = '6f7fda7bd1ce'
branch_labels = None
depends_on = None


def upgrade():
    # Add tax_period and findings columns to audit_cases table
    op.add_column('audit_cases', sa.Column('tax_period', sa.String(length=50), nullable=True))
    op.add_column('audit_cases', sa.Column('findings', sa.Text(), nullable=True))


def downgrade():
    # Remove the columns added in upgrade
    op.drop_column('audit_cases', 'findings')
    op.drop_column('audit_cases', 'tax_period')
