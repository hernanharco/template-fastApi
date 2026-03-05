# app/models/reminder.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import Base

class ScheduledReminder(Base):
    __tablename__ = "scheduled_reminders"

    id = Column(Integer, primary_key=True, index=True)
    
    # 🎯 RELACIÓN CON CASCADE: Si se borra la cita, se borra el recordatorio
    appointment_id = Column(
        Integer, 
        ForeignKey("appointments.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Datos de contacto
    phone = Column(String, index=True, nullable=True) # Para WhatsApp
    telegram_chat_id = Column(String, index=True, nullable=True) # Para el "Puente"
    
    # Configuración del mensaje
    message = Column(Text)
    scheduled_for = Column(DateTime, index=True)
    sent = Column(Boolean, default=False)
    
    # 🚀 CONTROL DE CANAL
    # Aquí guardamos si el dueño/cliente eligió 'whatsapp' o 'telegram'
    prefer_channel = Column(String, default="pendiente") 

    # Relación opcional para acceder a los datos de la cita desde el recordatorio
    appointment = relationship("Appointment", back_populates="reminders")