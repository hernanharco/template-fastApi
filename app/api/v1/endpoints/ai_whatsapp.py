from fastapi import APIRouter, Request, Response, Query, Depends
from sqlalchemy.orm import Session
from rich.console import Console
import traceback

from app.db.session import get_db
from app.core.config import settings
from app.services.whatssap import send_whatsapp_message, send_presence
from app.agents.core.maria_master import maria_master

router = APIRouter()
console = Console()

VERIFY_TOKEN = settings.SECRET_KEY


@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Endpoint de verificación para WhatsApp Cloud API.
    """

    console.print("[cyan]Webhook verification request received[/cyan]")
    console.print(f"hub.mode={hub_mode}")
    console.print(f"hub.verify_token={hub_verify_token}")
    console.print(f"hub.challenge={hub_challenge}")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        console.print("[green]Webhook verified successfully[/green]")
        return Response(content=hub_challenge, media_type="text/plain")

    console.print("[red]Webhook verification failed[/red]")
    return Response(content="Verification failed", status_code=403)


@router.post("/whatsapp")
async def handle_whatsapp_message(
    request: Request,
    db: Session = Depends(get_db)
):
    user_phone = "unknown"

    try:
        body = await request.json()

        console.print("[cyan]Webhook body recibido:[/cyan]")
        console.print(body)

        entry = body.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]
        value = change.get("value", {})

        if "messages" not in value:
            console.print("[yellow]Evento ignorado: no contiene messages[/yellow]")
            return {"status": "ignored"}

        message_data = value["messages"][0]

        user_phone = message_data.get("from")
        user_text = message_data.get("text", {}).get("body")

        console.print(f"[magenta]PHONE:[/magenta] {user_phone}")
        console.print(f"[magenta]TEXT:[/magenta] {user_text}")

        if not user_text:
            console.print("[yellow]Evento ignorado: mensaje sin texto[/yellow]")
            return {"status": "ignored"}

        await send_presence(user_phone, "typing_on")

        response_data = await maria_master.process_message(
            phone=user_phone,
            user_input=user_text
        )

        console.print("[blue]Response data MariaMaster:[/blue]")
        console.print(response_data)

        ai_response_text = response_data.get("text")

        if ai_response_text:
            await send_whatsapp_message(user_phone, ai_response_text)

        await send_presence(user_phone, "typing_off")

    except Exception as e:
        console.print(f"[red]Webhook error[/red] {str(e)}")
        console.print(traceback.format_exc())

        try:
            await send_presence(user_phone, "typing_off")
        except Exception:
            pass

        try:
            await send_whatsapp_message(
                user_phone,
                "Hubo un problema procesando tu mensaje. Intenta nuevamente."
            )
        except Exception:
            pass

    return {"status": "success"}