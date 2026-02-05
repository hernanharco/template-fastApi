# Importamos todos los esquemas para que estén disponibles cuando se importe este paquete
from .services import ServiceCreate, ServiceRead, ServiceUpdate
from .business_hours import BusinessHoursCreate, BusinessHoursRead, BusinessHoursUpdate, TimeSlotCreate, TimeSlotRead, TimeSlotUpdate
from .collaborators import CollaboratorCreate, CollaboratorRead, CollaboratorUpdate
from .appointments import AppointmentCreate, AppointmentRead, AppointmentUpdate, TimeSlot, AvailableSlotsResponse

__all__ = [
    "ServiceCreate", "ServiceRead", "ServiceUpdate",
    "BusinessHoursCreate", "BusinessHoursRead", "BusinessHoursUpdate",
    "TimeSlotCreate", "TimeSlotRead", "TimeSlotUpdate",
    "CollaboratorCreate", "CollaboratorRead", "CollaboratorUpdate",
    "AppointmentCreate", "AppointmentRead", "AppointmentUpdate",
    "TimeSlot", "AvailableSlotsResponse"
]
