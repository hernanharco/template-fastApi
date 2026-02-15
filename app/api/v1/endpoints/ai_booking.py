from fastapi import APIRouter, Request, Response, Query, Depends
from sqlalchemy.orm import Session
from app.agents.main_master import ValeriaMaster
from app.db.session import get_db # Importa tu generador de sesión
import httpx
from app.core.settings import settings

router = APIRouter()

# Instanciamos el Master una sola vez (es un objeto pesado)
master_agent = ValeriaMaster()

VERIFY_TOKEN = "mi_token_secreto_123"
WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN
PHONE_NUMBER_ID = settings.PHONE_NUMBER_ID
WHATSAPP_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

@router.get("/whatsapp")
async def verify_whatsapp(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Error", status_code=403)

@router.post("/whatsapp")
async def handle_whatsapp_message(
    request: Request, 
    db: Session = Depends(get_db) # <<< IMPORTANTE: Pedimos la sesión de Neon
):
    try:
        body = await request.json()
        
        # 1. Extraer datos de Meta
        entry = body.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        
        if 'messages' in value:
            message_data = value['messages'][0]
            user_phone = message_data['from']
            user_text = message_data['text']['body']
            
            # --- 🧠 PROCESO DE IA ---
            
            # TODO: Aquí podrías buscar el historial en tu tabla de 'conversations'
            # Por ahora pasamos una lista vacía para que el Master lo gestione
            history = [] 

            # Llamamos al método process que terminamos de arreglar antes
            # Recuerda: process devuelve (respuesta_texto, nuevo_historial)
            ai_response, _ = master_agent.process(
                db=db, 
                phone=user_phone, 
                message=user_text, 
                history=history
            )
            
            # --- 📲 ENVÍO A WHATSAPP ---
            async with httpx.AsyncClient() as client:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": user_phone,
                    "type": "text",
                    "text": {"body": ai_response}
                }
                headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                
                await client.post(WHATSAPP_URL, json=payload, headers=headers)
                print(f"✅ Respondido a {user_phone} via WhatsApp")

    except Exception as e:
        print(f"❌ Error en Webhook: {str(e)}")
        
    return {"status": "success"}