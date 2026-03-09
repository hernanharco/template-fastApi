IMPORTANT_PATTERNS = [
    "mi nombre es",
    "me llamo",
    "soy ",
    "me gusta",
    "tengo alergia",
    "no puedo comer",
]


def detect_memory(text: str):

    text_lower = text.lower()

    for pattern in IMPORTANT_PATTERNS:
        if pattern in text_lower:
            return text

    return None


# Esto sirve para detectar cosas importantes como:
# "mi nombre es Carlos"
# "me gusta el café"
# "soy alérgico al gluten"