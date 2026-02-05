"""
API Router para la gestión de colaboradores.
Este módulo contiene todos los endpoints CRUD para el dominio de colaboradores.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# Importaciones con rutas absolutas como se requiere
from app.db.session import get_db
from app.models.collaborators import Collaborator
from app.schemas.collaborators import CollaboratorCreate, CollaboratorRead, CollaboratorUpdate

# Creamos el router de FastAPI para este dominio
router = APIRouter()


@router.post("/", response_model=CollaboratorRead, status_code=status.HTTP_201_CREATED)
async def create_collaborator(
    collaborator_data: CollaboratorCreate, 
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo colaborador en el sistema.
    
    Args:
        collaborator_data: Datos del colaborador a crear
        db: Sesión de base de datos (inyectada automáticamente)
    
    Returns:
        CollaboratorRead: El colaborador creado con su ID
    
    Raises:
        HTTPException: Si ya existe un colaborador con el mismo email
    """
    # Si se proporciona email, verificamos que no exista otro colaborador activo con ese email
    if collaborator_data.email:
        existing_collaborator = db.query(Collaborator).filter(
            and_(
                Collaborator.email == collaborator_data.email.lower(),
                Collaborator.is_active == True
            )
        ).first()
        
        if existing_collaborator:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un colaborador activo con el email '{collaborator_data.email}'"
            )
    
    # Creamos el nuevo colaborador
    new_collaborator = Collaborator(
        name=collaborator_data.name,
        email=collaborator_data.email.lower() if collaborator_data.email else None,
        is_active=True
    )
    
    # Guardamos en la base de datos
    db.add(new_collaborator)
    db.commit()
    db.refresh(new_collaborator)
    
    return new_collaborator


@router.get("/", response_model=List[CollaboratorRead])
async def get_collaborators(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver"),
    active_only: bool = Query(True, description="Filtrar solo colaboradores activos"),
    search: Optional[str] = Query(None, description="Buscar por nombre o email"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de colaboradores con filtros opcionales.
    
    Args:
        skip: Número de registros a omitir (para paginación)
        limit: Número máximo de registros a devolver
        active_only: Si es True, solo devuelve colaboradores activos
        search: Término de búsqueda para filtrar por nombre o email
        db: Sesión de base de datos
    
    Returns:
        List[CollaboratorRead]: Lista de colaboradores encontrados
    """
    query = db.query(Collaborator)
    
    # Aplicamos filtros
    if active_only:
        query = query.filter(Collaborator.is_active == True)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Collaborator.name.ilike(search_term),
                Collaborator.email.ilike(search_term)
            )
        )
    
    # Aplicamos paginación y ordenamiento
    collaborators = query.order_by(Collaborator.name).offset(skip).limit(limit).all()
    
    return collaborators


@router.get("/{collaborator_id}", response_model=CollaboratorRead)
async def get_collaborator(
    collaborator_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un colaborador específico por su ID.
    
    Args:
        collaborator_id: ID del colaborador a buscar
        db: Sesión de base de datos
    
    Returns:
        CollaboratorRead: El colaborador encontrado
    
    Raises:
        HTTPException: Si el colaborador no existe
    """
    collaborator = db.query(Collaborator).filter(Collaborator.id == collaborator_id).first()
    
    if not collaborator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Colaborador con ID {collaborator_id} no encontrado"
        )
    
    return collaborator


@router.put("/{collaborator_id}", response_model=CollaboratorRead)
async def update_collaborator(
    collaborator_id: int,
    collaborator_data: CollaboratorUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un colaborador existente.
    
    Args:
        collaborator_id: ID del colaborador a actualizar
        collaborator_data: Datos a actualizar
        db: Sesión de base de datos
    
    Returns:
        CollaboratorRead: El colaborador actualizado
    
    Raises:
        HTTPException: Si el colaborador no existe o hay conflicto de emails
    """
    # Buscamos el colaborador existente
    collaborator = db.query(Collaborator).filter(Collaborator.id == collaborator_id).first()
    
    if not collaborator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Colaborador con ID {collaborator_id} no encontrado"
        )
    
    # Si se está actualizando el email, verificamos que no exista otro colaborador con ese email
    if collaborator_data.email and collaborator_data.email != collaborator.email:
        existing_collaborator = db.query(Collaborator).filter(
            and_(
                Collaborator.email == collaborator_data.email.lower(),
                Collaborator.id != collaborator_id,
                Collaborator.is_active == True
            )
        ).first()
        
        if existing_collaborator:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otro colaborador activo con el email '{collaborator_data.email}'"
            )
    
    # Actualizamos solo los campos proporcionados
    update_data = collaborator_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'email' and value:
            setattr(collaborator, field, value.lower())  # Normalizar email a minúsculas
        else:
            setattr(collaborator, field, value)
    
    # Guardamos los cambios
    db.commit()
    db.refresh(collaborator)
    
    return collaborator


@router.delete("/{collaborator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collaborator(
    collaborator_id: int,
    hard_delete: bool = Query(False, description="Si es True, elimina permanentemente el registro"),
    db: Session = Depends(get_db)
):
    """
    Elimina un colaborador (soft delete por defecto).
    
    Args:
        collaborator_id: ID del colaborador a eliminar
        hard_delete: Si es True, elimina permanentemente el registro
        db: Sesión de base de datos
    
    Raises:
        HTTPException: Si el colaborador no existe
    """
    collaborator = db.query(Collaborator).filter(Collaborator.id == collaborator_id).first()
    
    if not collaborator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Colaborador con ID {collaborator_id} no encontrado"
        )
    
    if hard_delete:
        # Eliminación permanente (solo para administradores)
        db.delete(collaborator)
    else:
        # Soft delete: marcamos como inactivo
        collaborator.is_active = False
    
    db.commit()


@router.get("/stats/summary")
async def get_collaborators_summary(db: Session = Depends(get_db)):
    """
    Obtiene un resumen estadístico de los colaboradores.
    
    Args:
        db: Sesión de base de datos
    
    Returns:
        dict: Resumen con estadísticas de colaboradores
    """
    total_collaborators = db.query(Collaborator).count()
    active_collaborators = db.query(Collaborator).filter(Collaborator.is_active == True).count()
    inactive_collaborators = total_collaborators - active_collaborators
    
    # Colaboradores con email
    collaborators_with_email = db.query(Collaborator).filter(
        and_(Collaborator.email.isnot(None), Collaborator.is_active == True)
    ).count()
    
    return {
        "total_collaborators": total_collaborators,
        "active_collaborators": active_collaborators,
        "inactive_collaborators": inactive_collaborators,
        "collaborators_with_email": collaborators_with_email,
        "email_coverage_percentage": round(
            (collaborators_with_email / active_collaborators * 100) if active_collaborators > 0 else 0, 2
        )
    }
