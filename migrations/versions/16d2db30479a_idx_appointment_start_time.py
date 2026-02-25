"""idx_appointment_start_time

Revision ID: 16d2db30479a
Revises: e75790f8a2b5
Create Date: 2026-02-22 18:09:44.129669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16d2db30479a'
down_revision: Union[str, Sequence[str], None] = 'e75790f8a2b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Comentamos esto porque ya existe en Neon
    # op.create_index('ix_appointments_start_time', 'appointments', ['start_time'])
    pass # <-- Importante para que no haga nada esta vez


def downgrade() -> None:
    """Downgrade schema."""
    # ### 🔙 Eliminamos el índice si decidimos volver atrás ###
    op.drop_index('ix_appointments_start_time', table_name='appointments')
    # ### end Alembic commands ###
