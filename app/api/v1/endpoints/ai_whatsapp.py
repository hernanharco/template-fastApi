# app/api/v1/endpoints/whatsapp.py
from fastapi import APIRouter, Request, Response, Query, Depends
from sqlalchemy.orm import Session
import httpx
import traceback

from app.agents.core.maria_master import maria  # Tu instancia de LangGraph
from app.db.session import get_db
from app.core.settings import settings
from app.api.v1.endpoints.notifications import notify_appointment_change # 🎯 El "avisador" SSE

router = APIRouter()

VERIFY_TOKEN = settings.SECRET_KEY
WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN
PHONE_NUMBER_ID = settings.PHONE_NUMBER_ID
WHATSAPP_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

@router.get("/whatsapp")
async def verify_whatsapp(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """Verificación del Webhook para Meta API."""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Error", status_code=403)

@router.post("/whatsapp")
async def handle_whatsapp_message(
    request: Request, 
    db: Session = Depends(get_db)
):
    try:
        body = await request.json()
        
        # 1. Filtro de seguridad: Solo procesamos si hay mensajes (ignoramos status: 'sent', 'delivered', etc.)
        value = body.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {})
        if 'messages' not in value:
            return {"status": "ignored_event"}

        message_data = value['messages'][0]
        user_phone = message_data['from']
        
        # Solo procesamos si es tipo texto para evitar errores con imágenes/audios por ahora
        if message_data.get('type') != 'text':
            return {"status": "not_text_type"}
            
        user_text = message_data.get('text', {}).get('body', "")

        # --- 🧠 PROCESO DE IA ---
        # 💡 TIP: Modifica tu maria.process para que devuelva un dict: 
        # {"text": "Respuesta...", "has_changes": True/False}
        result = maria.process(
            db=db, 
            phone=user_phone, 
            user_input=user_text
        )
        
        # Si maria.process devuelve directamente el string, 
        # puedes buscar palabras clave o mejor aún, adaptar el método process.
        ai_response = result.get("text") if isinstance(result, dict) else result
        has_changes = result.get("has_changes", False) if isinstance(result, dict) else True

        # --- 🚀 DISPARO TIEMPO REAL (SSE) CONDICIONAL ---
        # Solo notificamos si la IA detectó que hizo un cambio en la agenda
        if has_changes:
            # Comentado para evitar el error de argumentos y duplicidad.
            # El nodo de confirmación se encarga de llamar a notify_appointment_change
            # con los datos reales del cliente y servicio.
            # print(f"🔔 [REALTIME] Cambio detectado por María. Notificando al frontend...")
            # await notify_appointment_change()
            pass
        else:
            print(f"🤫 [REALTIME] Conversación informativa. No se requiere refresco.")

        # --- 📲 ENVÍO DE RESPUESTA A WHATSAPP ---
        # (Tu código de httpx se mantiene igual...)
        async with httpx.AsyncClient() as client:
            payload = {
                "messaging_product": "whatsapp",
                "to": user_phone,
                "type": "text",
                "text": {"body": ai_response}
            }
            headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
            await client.post(WHATSAPP_URL, json=payload, headers=headers)

    except Exception as e:
        print(f"❌ Error Crítico en Webhook: {str(e)}")
        
    return {"status": "success"}