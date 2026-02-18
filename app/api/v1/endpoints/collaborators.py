from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.collaborators import Collaborator
from app.models.departments import Department
from app.schemas.collaborators import CollaboratorCreate, CollaboratorRead, CollaboratorUpdate

router = APIRouter()

@router.post("/", response_model=CollaboratorRead, status_code=status.HTTP_201_CREATED)
def create_collaborator(data: CollaboratorCreate, db: Session = Depends(get_db)):
    new_collab = Collaborator(name=data.name, email=data.email)
    
    # Relacionar departamentos si vienen en el body
    if data.department_ids:
        db_depts = db.query(Department).filter(Department.id.in_(data.department_ids)).all()
        new_collab.departments = db_depts 

    db.add(new_collab)
    db.commit()
    # Usamos refresh para obtener los datos generados (id, created_at)
    db.refresh(new_collab)
    return new_collab

@router.get("/", response_model=List[CollaboratorRead])
def get_collaborators(active_only: bool = True, db: Session = Depends(get_db)):
    # Agregamos joinedload para traer los departamentos asociados en una sola consulta
    query = db.query(Collaborator).options(joinedload(Collaborator.departments))
    
    if active_only:
        query = query.filter(Collaborator.is_active == True)
        
    return query.order_by(Collaborator.name).all()

@router.get("/{collaborator_id}", response_model=CollaboratorRead)
def get_collaborator(collaborator_id: int, db: Session = Depends(get_db)):
    # También aplicamos joinedload aquí para las consultas individuales
    collab = db.query(Collaborator)\
        .options(joinedload(Collaborator.departments))\
        .filter(Collaborator.id == collaborator_id)\
        .first()
        
    if not collab:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")
    return collab

@router.put("/{collaborator_id}", response_model=CollaboratorRead)
def update_collaborator(collaborator_id: int, data: CollaboratorUpdate, db: Session = Depends(get_db)):
    # Cargamos el colaborador con sus departamentos actuales para poder modificarlos
    collab = db.query(Collaborator)\
        .options(joinedload(Collaborator.departments))\
        .filter(Collaborator.id == collaborator_id)\
        .first()
        
    if not collab:
        raise HTTPException(status_code=404, detail="No encontrado")

    update_dict = data.model_dump(exclude_unset=True)
    
    # Sincronización de la tabla intermedia (Many-to-Many)
    if "department_ids" in update_dict:
        ids = update_dict.pop("department_ids")
        # Buscamos los nuevos objetos de departamento y los asignamos a la relación
        collab.departments = db.query(Department).filter(Department.id.in_(ids)).all()

    # Actualizamos el resto de campos (name, email, is_active)
    for key, value in update_dict.items():
        setattr(collab, key, value)

    db.commit()
    db.refresh(collab)
    return collab

@router.delete("/{collaborator_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collaborator(collaborator_id: int, db: Session = Depends(get_db)):
    collab = db.query(Collaborator).filter(Collaborator.id == collaborator_id).first()
    if not collab:
        raise HTTPException(status_code=404, detail="No encontrado")
    
    # Siguiendo tu lógica de borrado lógico
    collab.is_active = False 
    db.commit()