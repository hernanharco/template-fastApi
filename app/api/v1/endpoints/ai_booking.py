from fastapi import APIRouter, Request, Response, Query
from app.agents.main_master import ValeriaMaster
import httpx
import json
from app.core.settings import settings

router = APIRouter()

# --- CONFIGURACIÓN DE META ---
# Recuerda que el WHATSAPP_TOKEN es temporal (24h). 
# Si deja de funcionar, genera uno nuevo en el panel de Meta.
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
    """
    Paso obligatorio para que Meta valide que tu servidor existe y es seguro.
    """
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado correctamente por Meta")
        return Response(content=challenge, media_type="text/plain")
    
    print("❌ Fallo en la verificación del Webhook")
    return Response(content="Error de verificación", status_code=403)

@router.post("/whatsapp")
async def handle_whatsapp_message(request: Request):
    """
    Recibe los mensajes del usuario, procesa con IA y responde.
    """
    try:
        body = await request.json()
        
        # Estructura de Meta para extraer el mensaje
        entry = body.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        
        if 'messages' in value:
            message = value['messages'][0]
            user_phone = message['from']
            user_text = message['text']['body']
            
            print(f"📩 Mensaje recibido de {user_phone}: {user_text}")
            
            # 1. Ejecutar el Agente de IA (Consulta disponibilidad en Neon)
            ai_response = ValeriaMaster(user_text)
            
            # 2. Enviar respuesta de vuelta a WhatsApp
            async with httpx.AsyncClient() as client:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": user_phone,
                    "type": "text",
                    "text": {"body": ai_response}
                }
                headers = {
                    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(WHATSAPP_URL, json=payload, headers=headers)
                
                # --- BLOQUE DE DEBUG PARA EL JUNIOR ---
                print(f"📡 Intentando enviar respuesta...")
                if response.status_code == 200:
                    print(f"✅ Respuesta enviada con éxito a {user_phone}")
                else:
                    print(f"⚠️ Error al enviar a Meta. Status: {response.status_code}")
                    print(f"🔍 Detalle del error de Meta: {response.text}")
                # --------------------------------------

    except Exception as e:
        print(f"❌ Error crítico procesando el webhook: {str(e)}")
        
    return {"status": "success"}