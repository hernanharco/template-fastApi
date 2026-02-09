"""
API Router para la gestión de servicios.
Este módulo contiene todos los endpoints CRUD para el dominio de servicios.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# Importaciones con rutas absolutas como se requiere
from app.db.session import get_db
from app.models.services import Service
from app.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate

# Creamos el router de FastAPI para este dominio
router = APIRouter()

@router.post("/", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_data: ServiceCreate, 
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo servicio en el sistema.
    
    Args:
        service_data: Datos del servicio a crear
        db: Sesión de base de datos (inyectada automáticamente)
    
    Returns:
        ServiceRead: El servicio creado con su ID
    
    Raises:
        HTTPException: Si ya existe un servicio con el mismo nombre
    """
    # Verificamos si ya existe un servicio con el mismo nombre
    existing_service = db.query(Service).filter(
        and_(Service.name == service_data.name, Service.is_active == True)
    ).first()
    
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un servicio activo con el nombre '{service_data.name}'"
        )
    
    # Creamos el nuevo servicio
    new_service = Service(
        name=service_data.name,
        duration_minutes=service_data.duration_minutes,
        price=service_data.price,
        is_active=True
    )
    
    # Guardamos en la base de datos
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    
    return new_service


@router.get("/", response_model=List[ServiceRead])
async def get_services(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver"),
    active_only: bool = Query(True, description="Filtrar solo servicios activos"),
    search: Optional[str] = Query(None, description="Buscar por nombre de servicio"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de servicios con filtros opcionales.
    
    Args:
        skip: Número de registros a omitir (para paginación)
        limit: Número máximo de registros a devolver
        active_only: Si es True, solo devuelve servicios activos
        search: Término de búsqueda para filtrar por nombre
        db: Sesión de base de datos
    
    Returns:
        List[ServiceRead]: Lista de servicios encontrados
    """
    query = db.query(Service)
    
    # Aplicamos filtros
    if active_only:
        query = query.filter(Service.is_active == True)
    
    if search:
        query = query.filter(Service.name.ilike(f"%{search}%"))
    
    # Aplicamos paginación
    services = query.offset(skip).limit(limit).all()
    
    return [ServiceRead.from_orm(service) for service in services]


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un servicio específico por su ID.
    
    Args:
        service_id: ID del servicio a buscar
        db: Sesión de base de datos
    
    Returns:
        ServiceRead: El servicio encontrado
    
    Raises:
        HTTPException: Si el servicio no existe
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {service_id} no encontrado"
        )
    
    return ServiceRead.from_orm(service)


@router.put("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un servicio existente.
    
    Args:
        service_id: ID del servicio a actualizar
        service_data: Datos a actualizar
        db: Sesión de base de datos
    
    Returns:
        ServiceRead: El servicio actualizado
    
    Raises:
        HTTPException: Si el servicio no existe o hay conflicto de nombres
    """
    # Buscamos el servicio existente
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {service_id} no encontrado"
        )
    
    # Si se está actualizando el nombre, verificamos que no exista otro servicio con ese nombre
    if service_data.name and service_data.name != service.name:
        existing_service = db.query(Service).filter(
            and_(
                Service.name == service_data.name,
                Service.id != service_id,
                Service.is_active == True
            )
        ).first()
        
        if existing_service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otro servicio activo con el nombre '{service_data.name}'"
            )
    
    # Actualizamos solo los campos proporcionados
    update_data = service_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    # Guardamos los cambios
    db.commit()
    db.refresh(service)
    
    return ServiceRead.from_orm(service)


@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    hard_delete: bool = Query(False, description="Si es True, elimina permanentemente el registro"),
    db: Session = Depends(get_db)
):
    """
    Elimina un servicio (soft delete por defecto).
    
    Args:
        service_id: ID del servicio a eliminar
        hard_delete: Si es True, elimina permanentemente el registro
        db: Sesión de base de datos
    
    Raises:
        HTTPException: Si el servicio no existe
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {service_id} no encontrado"
        )
    
    if hard_delete:
        # Eliminación permanente (solo para administradores)
        db.delete(service)
    else:
        # Soft delete: marcamos como inactivo
        service.is_active = False
    
    db.commit()
    
    return {"message": "Servicio eliminado exitosamente"}


@router.get("/stats/summary")
async def get_services_summary(db: Session = Depends(get_db)):
    """
    Obtiene un resumen estadístico de los servicios.
    
    Args:
        db: Sesión de base de datos
    
    Returns:
        dict: Resumen con estadísticas de servicios
    """
    total_services = db.query(Service).count()
    active_services = db.query(Service).filter(Service.is_active == True).count()
    inactive_services = total_services - active_services
    
    # Precio promedio de los servicios activos
    from sqlalchemy import func
    avg_price = db.query(Service).filter(Service.is_active == True).with_entities(
        func.avg(Service.price)
    ).scalar() or 0
    
    # Duración promedio en minutos
    avg_duration = db.query(Service).filter(Service.is_active == True).with_entities(
        func.avg(Service.duration_minutes)
    ).scalar() or 0
    
    return {
        "total_services": total_services,
        "active_services": active_services,
        "inactive_services": inactive_services,
        "average_price": round(float(avg_price), 2),
        "average_duration_minutes": round(float(avg_duration), 1)
    }
