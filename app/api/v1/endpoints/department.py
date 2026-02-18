from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.departments import Department as DepartmentModel
from app.schemas.department import Department, DepartmentCreate, DepartmentUpdate

router = APIRouter()

@router.get("/", response_model=List[Department])
def read_departments(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Recuperar todos los departamentos.
    """
    departments = db.query(DepartmentModel).offset(skip).limit(limit).all()
    return departments

@router.post("/", response_model=Department, status_code=status.HTTP_201_CREATED)
def create_department(
    *,
    db: Session = Depends(get_db),
    department_in: DepartmentCreate
) -> Any:
    """
    Crear un nuevo departamento.
    """
    # Verificar si ya existe un departamento con ese nombre
    existing = db.query(DepartmentModel).filter(DepartmentModel.name == department_in.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Un departamento con este nombre ya existe."
        )
    
    db_obj = DepartmentModel(**department_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/{id}", response_model=Department)
def read_department(
    *,
    db: Session = Depends(get_db),
    id: int
) -> Any:
    """
    Obtener un departamento por ID.
    """
    department = db.query(DepartmentModel).filter(DepartmentModel.id == id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return department

@router.put("/{id}", response_model=Department)
def update_department(
    *,
    db: Session = Depends(get_db),
    id: int,
    department_in: DepartmentUpdate
) -> Any:
    """
    Actualizar un departamento existente.
    """
    # 1. Buscar si el departamento existe
    db_obj = db.query(DepartmentModel).filter(DepartmentModel.id == id).first()
    if not db_obj:
        raise HTTPException(
            status_code=404, 
            detail="Departamento no encontrado"
        )
    
    # 2. Convertir los datos de entrada a un diccionario, excluyendo lo que sea None
    update_data = department_in.model_dump(exclude_unset=True)
    
    # 3. Actualizar los atributos del objeto de base de datos
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete("/{id}", response_model=Department)
def delete_department(
    *,
    db: Session = Depends(get_db),
    id: int
) -> Any:
    db_obj = db.query(DepartmentModel).filter(DepartmentModel.id == id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    
    # VALIDACIÓN DE SEGURIDAD:
    # No permitir borrar si tiene servicios vinculados
    if db_obj.services:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar: Este departamento tiene servicios asociados. Reasígnalos primero."
        )

    db.delete(db_obj)
    db.commit()
    return db_obj