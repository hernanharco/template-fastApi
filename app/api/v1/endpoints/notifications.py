import asyncio
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

# Lista de colas en memoria (RAM) para mantener las conexiones SSE activas
stream_queues = []

@router.get("/stream")
async def appointment_stream(request: Request):
    async def event_generator():
        # Cada conexión (pestaña del navegador) tiene su propia cola
        queue = asyncio.Queue()
        stream_queues.append(queue)
        try:
            while True:
                # Si el barbero cierra la pestaña, desconectamos y liberamos RAM
                if await request.is_disconnected():
                    break
                
                # Esperamos el "grito" del backend (bloqueo asíncrono, no consume CPU)
                data = await queue.get()
                
                # Enviamos el evento con el nombre 'update' y los datos
                yield {
                    "event": "update",
                    "data": data # Aquí va el JSON con la info de la cita
                }
        finally:
            # Limpieza al desconectar
            if queue in stream_queues:
                stream_queues.remove(queue)

    return EventSourceResponse(event_generator())

# --- FUNCIÓN HELPER MEJORADA ---
async def notify_appointment_change(
    client_name: str = "Nuevo Cliente", 
    service_name: str = "Servicio", 
    start_time: str = "--:--"
):
    """
    SRP: Notifica a todos los clientes conectados sobre una nueva cita.
    No toca la base de datos (Neon). Envía info directamente desde la RAM.
    """    
    payload = {
        "type": "NEW_APPOINTMENT",
        "title": "✨ ¡Nueva Cita María!",
        "client": client_name,
        "service": service_name,
        "time": start_time
    }
    
    # Lo convertimos a string JSON para el envío
    message = json.dumps(payload)
    
    # Lo enviamos a cada navegador que tenga el dashboard abierto
    for queue in stream_queues:
        await queue.put(message)