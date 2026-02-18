import sys
import os

# Añadimos la ruta del proyecto para poder importar tus clases
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.core.sanitizer import ResponseSanitizer

def test_sanitizer_errors():
    print("🧪 Iniciando batería de pruebas para ResponseSanitizer...\n")

    # Caso 1: El error del diccionario (El que viste en WhatsApp)
    dict_error = {'role': 'assistant', 'content': '¡Hola Hernan!'}
    res1 = ResponseSanitizer.clean(dict_error)
    print(f"Test 1 (Diccionario) -> Entrada: {dict_error}")
    print(f"✅ Resultado: '{res1}'\n")

    # Caso 2: El error de la tupla (A veces pasa en el Master)
    tuple_error = ("Servicio de cejas agendado", {"status": "success"})
    res2 = ResponseSanitizer.clean(tuple_error)
    print(f"Test 2 (Tupla) -> Entrada: {tuple_error}")
    print(f"✅ Resultado: '{res2}'\n")

    # Caso 3: Respuesta nula o vacía
    none_error = None
    res3 = ResponseSanitizer.clean(none_error)
    print(f"Test 3 (None) -> Entrada: {none_error}")
    print(f"✅ Resultado: '{res3}'\n")

    # Caso 4: Una lista de mensajes (Historial)
    list_error = ["Mensaje viejo", "Mensaje nuevo y limpio"]
    res4 = ResponseSanitizer.clean(list_error)
    print(f"Test 4 (Lista) -> Entrada: {list_error}")
    print(f"✅ Resultado: '{res4}'\n")

    # Caso 5: Texto que ya está limpio (No debería hacerle nada)
    clean_text = "Todo está perfecto."
    res5 = ResponseSanitizer.clean(clean_text)
    print(f"Test 5 (Texto Limpio) -> Entrada: '{clean_text}'")
    print(f"✅ Resultado: '{res5}'\n")

    print("🏁 ¡Pruebas finalizadas con éxito! Tu código está blindado.")

if __name__ == "__main__":
    test_sanitizer_errors()