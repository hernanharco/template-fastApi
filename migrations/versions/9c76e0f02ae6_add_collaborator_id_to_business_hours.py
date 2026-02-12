"""add_collaborator_id_to_business_hours

Revision ID: 9c76e0f02ae6
Revises: 35ef602b9cbb
Create Date: 2026-02-09 17:01:15.298449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c76e0f02ae6'
down_revision: Union[str, Sequence[str], None] = '35ef602b9cbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Añadimos la columna a la tabla business_hours
    op.add_column('business_hours', sa.Column('collaborator_id', sa.Integer(), nullable=True))
    
    # 2. Creamos la relación (Foreign Key) con la tabla de colaboradores
    op.create_foreign_key(
        'fk_business_hours_collaborator',
        'business_hours',
        'collaborators',
        ['collaborator_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    # Pasos para deshacer el cambio
    op.drop_constraint('fk_business_hours_collaborator', 'business_hours', type_='foreignkey')
    op.drop_column('business_hours', 'collaborator_id')