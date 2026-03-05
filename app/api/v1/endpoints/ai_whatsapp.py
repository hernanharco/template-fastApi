from fastapi import APIRouter, Request, Response, Query, Depends
from sqlalchemy.orm import Session
from rich.console import Console
import traceback

from app.db.session import get_db
from app.core.config import settings
from app.services.whatssap import send_whatsapp_message, send_presence
# 🚩 ELIMINAMOS EL IMPORT LOCAL DEL GRAFO
# from app.agents.routing.graph import graph 

# 🟢 IMPORTAMOS TU NUEVA CLASE MASTER
from app.agents.core.maria_master import maria_master 

router = APIRouter()
console = Console()

VERIFY_TOKEN = settings.SECRET_KEY

# --- 🛰️ ENDPOINTS ---

@router.post("/whatsapp")
async def handle_whatsapp_message(
    request: Request, 
    db: Session = Depends(get_db)
):
    user_phone = "unknown"
    try:
        body = await request.json()
        
        # Extracción segura de datos
        entry = body.get('entry', [{}])[0]
        change = entry.get('changes', [{}])[0]
        value = change.get('value', {})
        
        if 'messages' not in value:
            return {"status": "ok"}

        message_data = value['messages'][0]
        user_phone = message_data.get('from')
        user_text = message_data.get('text', {}).get('body', "")

        # 1. Indicador de "Escribiendo..."
        await send_presence(user_phone, "typing_on")

        # 2. --- 🧠 PROCESO DE IA VÍA MARIA_MASTER ---
        # Ahora usamos el SDK que conecta con el servidor persistente
        response_data = await maria_master.process_message(
            phone=user_phone, 
            user_input=user_text
        )
        
        ai_response_text = response_data.get("text")
        
        # 3. --- 📲 ENVÍO DE RESPUESTA ---
        if ai_response_text:
            await send_whatsapp_message(user_phone, ai_response_text)
            console.print(f"[green]✅ Mensaje enviado a {user_phone}[/green]")
        
        await send_presence(user_phone, "typing_off")

    except Exception as e:
        console.print(f"[red]❌ Error Crítico en Webhook:[/red] {str(e)}")
        await send_presence(user_phone, "typing_off")
        
    return {"status": "success"}