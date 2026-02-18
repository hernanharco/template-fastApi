"""
API Router para la gestión de servicios.
Implementa el Principio de Responsabilidad Única (SRP) y Eager Loading.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

# Importaciones del núcleo del sistema
from app.db.session import get_db
from app.models.services import Service
from app.models.departments import Department
from app.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate

router = APIRouter()

@router.post("/", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_data: ServiceCreate, 
    db: Session = Depends(get_db)
):
    # 1. Validar que el departamento asignado exista
    dept = db.query(Department).filter(Department.id == service_data.department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El departamento con ID {service_data.department_id} no existe."
        )

    # 2. Verificar si ya existe un servicio con el mismo nombre activo
    existing_service = db.query(Service).filter(
        and_(Service.name == service_data.name, Service.is_active == True)
    ).first()
    
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un servicio activo con el nombre '{service_data.name}'"
        )
    
    # 3. Crear la instancia del modelo (Mapeo manual para asegurar department_id)
    new_service = Service(
        name=service_data.name,
        duration_minutes=service_data.duration_minutes,
        price=service_data.price,
        department_id=service_data.department_id,
        is_active=True
    )
    
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    
    return new_service


@router.get("/", response_model=List[ServiceRead])
async def get_services(
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    # Usamos joinedload para traer la info del departamento en una sola consulta SQL
    query = db.query(Service).options(joinedload(Service.department))
    
    if active_only:
        query = query.filter(Service.is_active == True)
    
    if search:
        query = query.filter(Service.name.ilike(f"%{search}%"))
    
    return query.order_by(Service.name).all()


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).options(joinedload(Service.department))\
        .filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    return service


@router.put("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db)
):
    # Buscamos con su relación
    service = db.query(Service).options(joinedload(Service.department))\
        .filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    # Si cambia el nombre, validar duplicados (excluyendo el actual)
    if service_data.name and service_data.name != service.name:
        dup = db.query(Service).filter(
            and_(Service.name == service_data.name, Service.id != service_id, Service.is_active == True)
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="Ese nombre de servicio ya está en uso")

    # Actualización dinámica
    update_data = service_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)
    
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}")
async def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="No encontrado")
    
    # Aplicamos Borrado Lógico (Soft Delete)
    service.is_active = False
    db.commit()
    
    return {"message": "Servicio desactivado correctamente"}


@router.get("/stats/summary")
async def get_services_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    stats = db.query(
        func.count(Service.id).label("total"),
        func.avg(Service.price).label("avg_price"),
        func.avg(Service.duration_minutes).label("avg_duration")
    ).filter(Service.is_active == True).first()
    
    return {
        "total_active_services": stats.total or 0,
        "average_price": round(float(stats.avg_price or 0), 2),
        "average_duration": round(float(stats.avg_duration or 0), 1)
    }