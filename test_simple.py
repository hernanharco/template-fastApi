from app.db.session import SessionLocal
from app.models.collaborators import Collaborator
from app.models.departments import Department

def configure_custom_team():
    db = SessionLocal()
    try:
        # 1. Obtenemos los departamentos por sus IDs correctos
        nails = db.query(Department).filter(Department.id == 2).first()
        hair = db.query(Department).filter(Department.id == 3).first()

        # 2. Obtenemos a los colaboradores por sus IDs (7 y 8)
        hernan = db.query(Collaborator).filter(Collaborator.id == 7).first()
        eliana = db.query(Collaborator).filter(Collaborator.id == 8).first()

        # 3. Aplicamos tu lógica personalizada
        if eliana and nails and hair:
            # Eliana trabaja en AMBOS
            eliana.departments = [nails, hair]
            print(f"✨ {eliana.name} configurada para: Uñas y Cabello")

        if hernan and hair:
            # Hernan SOLO en Cabello
            hernan.departments = [hair]
            print(f"✨ {hernan.name} configurado para: SOLO Cabello")

        db.commit()
        print("\n🚀 ¡Configuración de equipo guardada en Neon!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    configure_custom_team()