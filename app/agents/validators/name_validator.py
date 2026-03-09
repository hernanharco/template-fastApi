import re
from typing import Optional


MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 40

INVALID_EXACT_VALUES = {
    "hola",
    "hello",
    "buenas",
    "oye",
    "hey",
    "yo",
    "numero",
    "número",
    "name",
    "nombre",
    "pelo",
}

INVALID_PHRASES = [
    "yo soy",
    "soy batman",
    "soy superman",
    "me llamo pelo",
    "no te voy a decir",
    "adivina",
]


def normalize_person_name(text: str) -> str:
    """
    Limpia espacios extras y capitaliza palabras del posible nombre.
    """
    cleaned = " ".join(text.strip().split())
    return cleaned.title()


def basic_name_check(text: Optional[str]) -> bool:
    """
    Validación básica de si un texto podría ser un nombre personal.
    No intenta ser perfecta; solo filtra casos claramente malos.
    """
    if not text:
        return False

    cleaned = text.strip()

    if len(cleaned) < MIN_NAME_LENGTH or len(cleaned) > MAX_NAME_LENGTH:
        return False

    if cleaned.isdigit():
        return False

    lowered = cleaned.lower()

    if lowered in INVALID_EXACT_VALUES:
        return False

    for phrase in INVALID_PHRASES:
        if phrase in lowered:
            return False

    if len(cleaned.split()) > 3:
        return False

    pattern = r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]+$"
    if not re.match(pattern, cleaned):
        return False

    return True


def looks_like_real_name(text: Optional[str]) -> bool:
    """
    Regla práctica para validar nombres razonables sin usar todavía LLM.
    Acepta nombres cortos como Ian o Lia.
    """
    if not basic_name_check(text):
        return False

    cleaned = text.strip()
    lowered = cleaned.lower()

    # rechazar letras sueltas tipo "a"
    if len(cleaned) == 1:
        return False

    # permitir nombres cortos válidos de 2-3 letras
    # ej: Ian, Lia, Leo, Ana, Eva
    if 2 <= len(cleaned) <= 3:
        return True

    # una sola palabra larga puede ser válida, pero algunas palabras comunes no lo son
    common_non_names = {
        "pelo",
        "gato",
        "perro",
        "casa",
        "mesa",
        "azul",
        "rojo",
        "verde",
    }

    if lowered in common_non_names:
        return False

    return True