from typing import List

from app.schemas.services import ServiceRead


# Palabras clave → emoji. Se evalúan en orden, gana la primera coincidencia.
KEYWORD_EMOJIS = [
    # Cejas / ojos
    (["ceja", "depilacion ceja", "diseño ceja"],            "🪮"),
    # Cabello
    (["corte", "cabello", "pelo", "tinte", "mechas",
      "keratina", "alisado", "ondulado", "peinado"],        "✂️"),
    # Uñas acrílicas
    (["acril", "acrili", "acrílica"],                       "💎"),
    # Uñas en gel
    (["gel"],                                               "💜"),
    # Semi permanente (manos o pies)
    (["semi"],                                              "✨"),
    # Manicure genérico
    (["manic", "mano", "esmalte"],                          "💅"),
    # Pedicure genérico
    (["pedic", "pie"],                                      "🦶"),
    # Facial / rostro
    (["facial", "rostro", "limpieza", "hidrata",
      "mascarilla", "peeling"],                             "🧖"),
    # Masajes / corporales
    (["masaje", "corporal", "relaj"],                       "💆"),
    # Depilación
    (["depilac", "cera", "laser"],                          "🌿"),
    # Maquillaje
    (["maquillaje", "makeup", "novias"],                    "💄"),
    # Pestañas
    (["pestaña", "lash"],                                   "👁️"),
]

DEFAULT_EMOJI = "✨"


def _emoji_for(name: str) -> str:
    normalized = name.lower().strip()
    for keywords, emoji in KEYWORD_EMOJIS:
        if any(kw in normalized for kw in keywords):
            return emoji
    return DEFAULT_EMOJI


def format_catalog_for_whatsapp(services: List[ServiceRead], client_name: str | None = None) -> str:
    if not services:
        if client_name:
            return f"{client_name}, ahora mismo no tengo servicios disponibles."
        return "Ahora mismo no tengo servicios disponibles."

    header = "✨ Estos son nuestros servicios disponibles:"
    if client_name:
        header = f"✨ {client_name}, estos son nuestros servicios disponibles:"

    lines = [header, ""]

    for service in services[:10]:
        emoji = _emoji_for(service.name)
        lines.append(f"{emoji} *{service.name}*")

    lines.append("")
    lines.append("¿Cuál te interesa? 😊")

    return "\n".join(lines)