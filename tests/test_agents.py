"""
Suite de pruebas automatizadas — CoreAppointment
Cubre: extractor, flujo completo, cambio de servicio,
       memoria, confirmación y charla casual.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ✅ Carga el .env desde la raíz del proyecto sin importar desde dónde se ejecute
load_dotenv(Path(__file__).parent.parent / ".env")

from datetime import datetime, timedelta
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster
from app.models.clients import Client

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
TEST_PHONE = "000000001"  # teléfono exclusivo para tests — no usar en producción

VERDE  = "\033[92m"
ROJO   = "\033[91m"
AMARILLO = "\033[93m"
RESET  = "\033[0m"
LINEA  = "─" * 60


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def reset_cliente(db):
    cliente = db.query(Client).filter(Client.phone == TEST_PHONE).first()
    if cliente:
        cliente.current_service_id = None
        cliente.metadata_json = {}
        flag_modified(cliente, "metadata_json")
        db.commit()

def run_conversation(orch, db, pasos: list[tuple[str, str | None]]) -> list[dict]:
    """
    Ejecuta una conversación paso a paso.
    pasos: [(mensaje_usuario, texto_esperado_en_respuesta | None), ...]
    Devuelve lista de resultados por paso.
    """
    history  = []
    resultados = []

    for msg, esperado in pasos:
        respuesta, history = orch.process(db, TEST_PHONE, msg, history)
        ok = True
        if esperado:
            ok = esperado.lower() in respuesta.lower()
        resultados.append({
            "msg":       msg,
            "respuesta": respuesta,
            "esperado":  esperado,
            "ok":        ok
        })

    return resultados

def imprimir_resultados(nombre: str, resultados: list[dict]):
    print(f"\n{LINEA}")
    print(f"🧪 TEST: {nombre}")
    print(LINEA)
    aprobados = 0
    for i, r in enumerate(resultados, 1):
        icono = f"{VERDE}✅{RESET}" if r["ok"] else f"{ROJO}❌{RESET}"
        print(f"{icono} Paso {i}: '{r['msg']}'")
        print(f"   → Valeria: {r['respuesta'][:120]}")
        if r["esperado"] and not r["ok"]:
            print(f"   {ROJO}esperado contener: '{r['esperado']}'{RESET}")
        if r["ok"]:
            aprobados += 1
    total = len(resultados)
    color = VERDE if aprobados == total else AMARILLO if aprobados > 0 else ROJO
    print(f"\n{color}Resultado: {aprobados}/{total} pasos OK{RESET}")
    return aprobados, total


# ─────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────

def test_extractor_fechas(orch, db):
    """Verifica que el extractor resuelve fechas relativas correctamente."""
    hoy       = datetime.now()
    manana    = (hoy + timedelta(days=1)).strftime("%Y-%m-%d")
    pasado    = (hoy + timedelta(days=2)).strftime("%Y-%m-%d")
    dias_es   = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    lunes_diff = (0 - hoy.weekday()) % 7 or 7
    proximo_lunes = (hoy + timedelta(days=lunes_diff)).strftime("%Y-%m-%d")

    casos = [
        ("hoy",          hoy.strftime("%Y-%m-%d")),
        ("mañana",       manana),
        ("pasado mañana", pasado),
        ("el lunes",     proximo_lunes),
        ("el martes",    None),  # solo verificamos que no crashee
    ]

    resultados = []
    from app.agents.booking.nodes.extractor_node import extractor_node

    for msg, fecha_esperada in casos:
        state = {
            "messages":     [{"role": "user", "content": msg}],
            "current_date": hoy.strftime("%Y-%m-%d"),
        }
        result = extractor_node(state)
        date   = result.get("appointment_date")
        ok     = (date == fecha_esperada) if fecha_esperada else (date is not None)
        resultados.append({
            "msg":       msg,
            "respuesta": f"date={date}",
            "esperado":  fecha_esperada,
            "ok":        ok
        })

    return imprimir_resultados("Extractor de fechas", resultados)


def test_flujo_completo(orch, db):
    """Flujo ideal: saludo → servicio → fecha → slots → hora → confirmación."""
    reset_cliente(db)
    pasos = [
        ("hola quiero una cita",          "opciones"),
        ("uñas normales",                 "uñas normales"),
        ("mañana",                        None),           # slots o pide día
        ("10",                            None),           # intenta confirmar hora
    ]
    return imprimir_resultados("Flujo completo de reserva", run_conversation(orch, db, pasos))


def test_cambio_servicio(orch, db):
    """El usuario cambia de servicio a mitad del flujo."""
    reset_cliente(db)
    pasos = [
        ("quiero uñas normales",           "uñas normales"),
        ("no mejor uñas decoradas",        "uñas decoradas"),
        ("el viernes",                     None),
    ]
    return imprimir_resultados("Cambio de servicio", run_conversation(orch, db, pasos))


def test_memoria_entre_turnos(orch, db):
    """La fecha dicha antes del servicio se conserva."""
    reset_cliente(db)
    pasos = [
        ("cita para mañana",               "opciones"),       # muestra catálogo
        ("uñas pedicure",                  "mañana"),         # debe recordar mañana
    ]
    return imprimir_resultados("Memoria entre turnos", run_conversation(orch, db, pasos))


def test_keywords_confirmacion(orch, db):
    """'vale', 'ok', 'sí' no disparan charla casual cuando hay contexto de cita."""
    reset_cliente(db)
    pasos = [
        ("quiero uñas normales",           "uñas normales"),
        ("el lunes",                       None),
        ("vale",                           None),   # no debe responder como casual
    ]
    resultados = run_conversation(orch, db, pasos)
    # El último paso no debe inventar horarios
    ultimo = resultados[-1]
    inventado = any(w in ultimo["respuesta"].lower() for w in ["3:00", "5:00", "pm", "te agendo"])
    resultados[-1]["ok"] = not inventado
    resultados[-1]["esperado"] = "sin horarios inventados"
    return imprimir_resultados("Keywords de confirmación", resultados)


def test_franja_lunes_jueves(orch, db):
    """El usuario pide cita entre lunes y jueves — debe ofrecer slots en esos días."""
    reset_cliente(db)
    hoy_dt     = datetime.now()
    dias_es    = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    # Calculamos el próximo lunes y jueves para verificar
    lunes_diff = (0 - hoy_dt.weekday()) % 7 or 7
    lunes      = (hoy_dt + timedelta(days=lunes_diff)).strftime("%d/%m/%Y")
    jueves_diff = (3 - hoy_dt.weekday()) % 7 or 7
    jueves     = (hoy_dt + timedelta(days=jueves_diff)).strftime("%d/%m/%Y")

    pasos = [
        ("quiero uñas normales",                        "uñas normales"),
        ("buscarme una cita entre el lunes y el jueves", None),  # debe proponer día en esa franja
    ]
    resultados = run_conversation(orch, db, pasos)

    # Verificamos que la respuesta mencione un día dentro de lunes-jueves
    ultimo = resultados[-1]["respuesta"].lower()
    en_franja = any(d in ultimo for d in ["lunes","martes","miércoles","jueves", lunes, jueves])
    no_fuera  = not any(d in ultimo for d in ["viernes","sábado","domingo"])
    resultados[-1]["ok"]      = en_franja and no_fuera
    resultados[-1]["esperado"] = "día dentro de lunes-jueves"

    return imprimir_resultados("Franja lunes-jueves", resultados)


def test_antes_del_sabado(orch, db):
    """El usuario pide cita antes del sábado — debe ofrecer slots de lunes a viernes."""
    reset_cliente(db)
    hoy_dt = datetime.now()

    pasos = [
        ("quiero uñas normales",         "uñas normales"),
        ("antes del sábado por favor",   None),
    ]
    resultados = run_conversation(orch, db, pasos)

    ultimo = resultados[-1]["respuesta"].lower()
    # No debe proponer sábado ni domingo
    no_sabado  = "sábado" not in ultimo and "sabado" not in ultimo
    no_domingo = "domingo" not in ultimo
    # Debe proponer algo concreto (fecha o día)
    propone    = any(d in ultimo for d in ["lunes","martes","miércoles","jueves","viernes","/202"])
    resultados[-1]["ok"]      = no_sabado and no_domingo and propone
    resultados[-1]["esperado"] = "día antes del sábado, sin proponer sábado/domingo"

    return imprimir_resultados("Antes del sábado", resultados)


def test_casual_sin_inventar(orch, db):
    """Charla casual no debe inventar citas ni horarios."""
    reset_cliente(db)
    pasos = [
        ("hola cómo estás",   None),
        ("qué tal el tiempo", None),
        ("gracias",           None),
    ]
    resultados = run_conversation(orch, db, pasos)
    palabras_prohibidas = ["te agendo", "cita confirmada", "tengo disponibilidad", "pm", "am"]
    for r in resultados:
        inventado = any(w in r["respuesta"].lower() for w in palabras_prohibidas)
        if inventado:
            r["ok"]      = False
            r["esperado"] = "sin datos inventados"
    return imprimir_resultados("Charla casual sin inventar", resultados)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print("🚀 CoreAppointment — Suite de Tests Automatizados")
    print(f"{'='*60}")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📱 Teléfono de prueba: {TEST_PHONE}\n")

    orch = ValeriaMaster()
    db   = SessionLocal()

    total_ok    = 0
    total_pasos = 0

    try:
        tests = [
            test_extractor_fechas,
            test_flujo_completo,
            test_cambio_servicio,
            test_memoria_entre_turnos,
            test_keywords_confirmacion,
            test_franja_lunes_jueves,
            test_antes_del_sabado,
            test_casual_sin_inventar,
        ]

        for test_fn in tests:
            ok, total = test_fn(orch, db)
            total_ok    += ok
            total_pasos += total

    except Exception as e:
        import traceback
        print(f"\n{ROJO}❌ Error inesperado: {e}{RESET}")
        print(traceback.format_exc())

    finally:
        db.close()

    print(f"\n{'='*60}")
    color = VERDE if total_ok == total_pasos else AMARILLO if total_ok > total_pasos // 2 else ROJO
    print(f"{color}📊 RESULTADO FINAL: {total_ok}/{total_pasos} pasos aprobados{RESET}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()