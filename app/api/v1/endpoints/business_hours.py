"""
API Router para la gestión de horarios de negocio.
Este módulo contiene todos los endpoints CRUD para el dominio de horarios.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# Importaciones con rutas absolutas como se requiere
from app.db.session import get_db
from app.models.business_hours import BusinessHours, TimeSlot
from app.schemas.business_hours import (
    BusinessHoursCreate, BusinessHoursRead, BusinessHoursUpdate,
    TimeSlotCreate, TimeSlotRead, TimeSlotUpdate
)

# Creamos el router de FastAPI para este dominio
router = APIRouter()

@router.post("/", response_model=BusinessHoursRead, status_code=status.HTTP_201_CREATED)
async def create_business_hours(
    business_hours_data: BusinessHoursCreate,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva configuración de horarios para un día específico.
    
    Args:
        business_hours_data: Datos de los horarios a crear
        db: Sesión de base de datos (inyectada automáticamente)
    
    Returns:
        BusinessHoursRead: La configuración de horarios creada con su ID
    
    Raises:
        HTTPException: Si ya existe una configuración para ese día
    """
    # Verificamos si ya existe una configuración para ese día
    existing_hours = db.query(BusinessHours).filter(
        BusinessHours.day_of_week == business_hours_data.day_of_week
    ).first()
    
    if existing_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una configuración de horarios para {business_hours_data.day_name}"
        )
    
    # Creamos la configuración principal de horarios
    new_business_hours = BusinessHours(
        day_of_week=business_hours_data.day_of_week,
        day_name=business_hours_data.day_name,
        is_enabled=business_hours_data.is_enabled,
        is_split_shift=business_hours_data.is_split_shift
    )
    
    db.add(new_business_hours)
    db.flush()  # Obtenemos el ID sin hacer commit todavía
    
    # Creamos los slots de tiempo asociados
    for slot_data in business_hours_data.time_slots:
        # Convertimos las horas de string a objetos time
        from datetime import datetime
        start_time = datetime.strptime(slot_data.start_time, "%H:%M").time()
        end_time = datetime.strptime(slot_data.end_time, "%H:%M").time()
        
        new_slot = TimeSlot(
            start_time=start_time,
            end_time=end_time,
            slot_order=slot_data.slot_order,
            business_hours_id=new_business_hours.id
        )
        db.add(new_slot)
    
    # Guardamos todo en la base de datos
    db.commit()
    db.refresh(new_business_hours)
    
    return new_business_hours


@router.get("/", response_model=List[BusinessHoursRead])
async def get_business_hours(
    enabled_only: bool = Query(False, description="Filtrar solo días habilitados"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista completa de configuraciones de horarios.
    
    Args:
        enabled_only: Si es True, solo devuelve días habilitados
        db: Sesión de base de datos
    
    Returns:
        List[BusinessHoursRead]: Lista de configuraciones de horarios
    """
    query = db.query(BusinessHours)
    
    if enabled_only:
        query = query.filter(BusinessHours.is_enabled == True)
    
    # Ordenamos por día de la semana para que venga en orden lógico
    business_hours = query.order_by(BusinessHours.day_of_week).all()
    
    return BusinessHoursRead.from_orm(business_hours)


@router.get("/{business_hours_id}", response_model=BusinessHoursRead)
async def get_business_hours_by_id(
    business_hours_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una configuración de horarios específica por su ID.
    
    Args:
        business_hours_id: ID de la configuración a buscar
        db: Sesión de base de datos
    
    Returns:
        BusinessHoursRead: La configuración encontrada
    
    Raises:
        HTTPException: Si la configuración no existe
    """
    business_hours = db.query(BusinessHours).filter(
        BusinessHours.id == business_hours_id
    ).first()
    
    if not business_hours:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración de horarios con ID {business_hours_id} no encontrada"
        )
    
    return BusinessHoursRead.from_orm(business_hours)


@router.get("/day/{day_name}", response_model=BusinessHoursRead)
async def get_business_hours_by_day(
    day_name: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene la configuración de horarios para un día específico.
    
    Args:
        day_name: Nombre del día (Lunes, Martes, etc.)
        db: Sesión de base de datos
    
    Returns:
        BusinessHoursRead: La configuración del día
    
    Raises:
        HTTPException: Si el día no es válido o no hay configuración
    """
    # Validamos que el día sea válido
    valid_days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    if day_name not in valid_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Día inválido. Debe ser uno de: {', '.join(valid_days)}"
        )
    
    business_hours = db.query(BusinessHours).filter(
        BusinessHours.day_name == day_name
    ).first()
    
    if not business_hours:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay configuración de horarios para {day_name}"
        )
    
    return BusinessHoursRead.from_orm(business_hours)


@router.put("/{business_hours_id}", response_model=BusinessHoursRead)
async def update_business_hours(
    business_hours_id: int,
    business_hours_data: BusinessHoursUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza una configuración de horarios existente.
    
    Args:
        business_hours_id: ID de la configuración a actualizar
        business_hours_data: Datos a actualizar
        db: Sesión de base de datos
    
    Returns:
        BusinessHoursRead: La configuración actualizada
    
    Raises:
        HTTPException: Si la configuración no existe
    """
    # Buscamos la configuración existente
    business_hours = db.query(BusinessHours).filter(
        BusinessHours.id == business_hours_id
    ).first()
    
    if not business_hours:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración de horarios con ID {business_hours_id} no encontrada"
        )
    
    # Actualizamos los campos principales si se proporcionan
    update_data = business_hours_data.dict(exclude_unset=True, exclude={'time_slots'})
    for field, value in update_data.items():
        setattr(business_hours, field, value)
    
    # Si se proporcionan nuevos time_slots, los actualizamos completamente
    if business_hours_data.time_slots is not None:
        # Eliminamos los slots existentes
        db.query(TimeSlot).filter(
            TimeSlot.business_hours_id == business_hours_id
        ).delete()
        
        # Creamos los nuevos slots
        for slot_data in business_hours_data.time_slots:
            from datetime import datetime
            start_time = datetime.strptime(slot_data.start_time, "%H:%M").time()
            end_time = datetime.strptime(slot_data.end_time, "%H:%M").time()
            
            new_slot = TimeSlot(
                start_time=start_time,
                end_time=end_time,
                slot_order=slot_data.slot_order,
                business_hours_id=business_hours.id
            )
            db.add(new_slot)
    
    # Guardamos los cambios
    db.commit()
    db.refresh(business_hours)
    
    return BusinessHoursRead.from_orm(business_hours)


@router.delete("/{business_hours_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_hours(
    business_hours_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina una configuración de horarios.
    
    Args:
        business_hours_id: ID de la configuración a eliminar
        db: Sesión de base de datos
    
    Raises:
        HTTPException: Si la configuración no existe
    """
    business_hours = db.query(BusinessHours).filter(
        BusinessHours.id == business_hours_id
    ).first()
    
    if not business_hours:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración de horarios con ID {business_hours_id} no encontrada"
        )
    
    # La eliminación en cascada se encargará de eliminar los time_slots
    db.delete(business_hours)
    db.commit()


@router.post("/initialize-week", response_model=List[BusinessHoursRead])
async def initialize_week_schedule(db: Session = Depends(get_db)):
    """
    Inicializa la configuración de horarios para toda la semana.
    Crea configuraciones básicas para todos los días si no existen.
    
    Args:
        db: Sesión de base de datos
    
    Returns:
        List[BusinessHoursRead]: Lista de configuraciones creadas/existentes
    """
    days_config = [
        {"day_of_week": 0, "day_name": "Lunes", "is_enabled": True, "is_split_shift": True},
        {"day_of_week": 1, "day_name": "Martes", "is_enabled": True, "is_split_shift": False},
        {"day_of_week": 2, "day_name": "Miércoles", "is_enabled": True, "is_split_shift": False},
        {"day_of_week": 3, "day_name": "Jueves", "is_enabled": True, "is_split_shift": False},
        {"day_of_week": 4, "day_name": "Viernes", "is_enabled": True, "is_split_shift": False},
        {"day_of_week": 5, "day_name": "Sábado", "is_enabled": True, "is_split_shift": False},
        {"day_of_week": 6, "day_name": "Domingo", "is_enabled": False, "is_split_shift": False},
    ]
    
    created_hours = []
    
    for day_config in days_config:
        # Verificamos si ya existe configuración para este día
        existing = db.query(BusinessHours).filter(
            BusinessHours.day_of_week == day_config["day_of_week"]
        ).first()
        
        if not existing:
            # Creamos la configuración básica
            new_hours = BusinessHours(
                day_of_week=day_config["day_of_week"],
                day_name=day_config["day_name"],
                is_enabled=day_config["is_enabled"],
                is_split_shift=day_config["is_split_shift"]
            )
            db.add(new_hours)
            db.flush()
            
            # Creamos slots por defecto según el tipo de turno
            if day_config["is_enabled"]:
                if day_config["is_split_shift"]:
                    # Turno partido: mañana y tarde
                    from datetime import datetime
                    morning_slot = TimeSlot(
                        start_time=datetime.strptime("09:00", "%H:%M").time(),
                        end_time=datetime.strptime("13:00", "%H:%M").time(),
                        slot_order=1,
                        business_hours_id=new_hours.id
                    )
                    afternoon_slot = TimeSlot(
                        start_time=datetime.strptime("16:00", "%H:%M").time(),
                        end_time=datetime.strptime("20:00", "%H:%M").time(),
                        slot_order=2,
                        business_hours_id=new_hours.id
                    )
                    db.add(morning_slot)
                    db.add(afternoon_slot)
                else:
                    # Turno único
                    from datetime import datetime
                    if day_config["day_name"] == "Sábado":
                        # Sábado con horario reducido
                        single_slot = TimeSlot(
                            start_time=datetime.strptime("10:00", "%H:%M").time(),
                            end_time=datetime.strptime("14:00", "%H:%M").time(),
                            slot_order=1,
                            business_hours_id=new_hours.id
                        )
                    else:
                        # Entre semana con horario completo
                        single_slot = TimeSlot(
                            start_time=datetime.strptime("09:00", "%H:%M").time(),
                            end_time=datetime.strptime("20:00", "%H:%M").time(),
                            slot_order=1,
                            business_hours_id=new_hours.id
                        )
                    db.add(single_slot)
            
            created_hours.append(new_hours)
        else:
            created_hours.append(existing)
    
    db.commit()
    
    # Refrescamos todos los objetos para obtener los datos completos
    for hours in created_hours:
        db.refresh(hours)
    
    return created_hours
