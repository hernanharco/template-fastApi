"""
Modelo base para SQLAlchemy.
Este archivo contiene la clase Base que heredarán todos nuestros modelos.
"""

from sqlalchemy.ext.declarative import declarative_base

# Base es la clase padre para todos los modelos SQLAlchemy
# Proporciona metadatos comunes y funcionalidad de mapeo objeto-relacional
Base = declarative_base()
