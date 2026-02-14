"""
Test focalizado — Solo los 3 casos que fallaron:
1. Memoria entre turnos
2. Franja lunes-jueves
3. Antes del sábado
"""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from datetime import datetime, timedelta
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster
from app.models.clients import Client

TEST_PHONE = "000000002"  # teléfono distinto para no mezclar con el suite principal

VERDE    = "\033[92m"
ROJO     = "\033[91m"
AMARILLO = "\033[93m"
RESET    = "\033[0m"
LINEA    = "─" * 60


def reset_cliente(db):
    cliente = db.query(Client).filter(Client.phone == TEST_PHONE).first()
    if cliente:
        cliente.current_service_id = None
        cliente.metadata_json = {}
        flag_modified(cliente, "metadata_json")
        db.commit()


def run_conversation(orch, db, pasos):
    history = []
    resultados = []
    for msg, esperado in pasos:
        respuesta, history = orch.process(db, TEST_PHONE, msg, history)
        ok = (esperado.lower() in respuesta.lower()) if esperado else True
        resultados.append({
            "msg":       msg,
            "respuesta": respuesta,
            "esperado":  esperado,
            "ok":        ok
        })
    return resultados


def imprimir(nombre, resultados):
    print(f"\n{LINEA}\n🧪 TEST: {nombre}\n{LINEA}")
    ok_count = 0
    for i, r in enumerate(resultados, 1):
        icono = f"{VERDE}✅{RESET}" if r["ok"] else f"{ROJO}❌{RESET}"
        print(f"{icono} Paso {i}: '{r['msg']}'")
        print(f"   → {r['respuesta'][:120]}")
        if r["esperado"] and not r["ok"]:
            print(f"   {ROJO}esperado: '{r['esperado']}'{RESET}")
        if r["ok"]:
            ok_count += 1
    color = VERDE if ok_count == len(resultados) else ROJO
    print(f"\n{color}Resultado: {ok_count}/{len(resultados)} pasos OK{RESET}")
    return ok_count, len(resultados)


# ─────────────────────────────────────────────
# TEST 1 — Memoria entre turnos
# ─────────────────────────────────────────────

def test_memoria(orch, db):
    reset_cliente(db)
    pasos = [
        ("cita para mañana",  "opciones"),   # catálogo + captura fecha
        ("uñas pedicure",     "mañana"),     # debe recordar mañana
    ]
    resultados = run_conversation(orch, db, pasos)

    # Debug extra: mostramos qué tiene el metadata_json tras el paso 1
    cliente = db.query(Client).filter(Client.phone == TEST_PHONE).first()
    fecha_db = cliente.metadata_json.get("appointment_date") if cliente.metadata_json else None
    print(f"\n   📋 appointment_date en DB tras paso 1: {fecha_db}")

    return imprimir("Memoria entre turnos", resultados)


# ─────────────────────────────────────────────
# TEST 2 — Franja lunes-jueves
# ─────────────────────────────────────────────

def test_franja(orch, db):
    reset_cliente(db)
    hoy_dt      = datetime.now()
    lunes_diff  = (0 - hoy_dt.weekday()) % 7 or 7
    jueves_diff = (3 - hoy_dt.weekday()) % 7 or 7
    lunes       = (hoy_dt + timedelta(days=lunes_diff)).strftime("%d/%m/%Y")
    jueves      = (hoy_dt + timedelta(days=jueves_diff)).strftime("%d/%m/%Y")

    pasos = [
        ("quiero uñas normales",                         "uñas normales"),
        ("buscarme una cita entre el lunes y el jueves", None),
    ]
    resultados = run_conversation(orch, db, pasos)

    ultimo    = resultados[-1]["respuesta"].lower()
    en_franja = any(d in ultimo for d in ["lunes","martes","miércoles","jueves", lunes, jueves])
    no_fuera  = not any(d in ultimo for d in ["viernes","sábado","domingo"])
    resultados[-1]["ok"]      = en_franja and no_fuera
    resultados[-1]["esperado"] = "día dentro de lunes-jueves"

    print(f"\n   📋 Respuesta completa: {resultados[-1]['respuesta']}")
    return imprimir("Franja lunes-jueves", resultados)


# ─────────────────────────────────────────────
# TEST 3 — Antes del sábado
# ─────────────────────────────────────────────

def test_antes_sabado(orch, db):
    reset_cliente(db)
    pasos = [
        ("quiero uñas normales",       "uñas normales"),
        ("antes del sábado por favor", None),
    ]
    resultados = run_conversation(orch, db, pasos)

    ultimo     = resultados[-1]["respuesta"].lower()
    no_sabado  = "sábado" not in ultimo and "sabado" not in ultimo
    no_domingo = "domingo" not in ultimo
    propone    = any(d in ultimo for d in ["lunes","martes","miércoles","jueves","viernes","/202"])
    resultados[-1]["ok"]      = no_sabado and no_domingo and propone
    resultados[-1]["esperado"] = "día antes del sábado, sin sábado/domingo"

    print(f"\n   📋 Respuesta completa: {resultados[-1]['respuesta']}")
    return imprimir("Antes del sábado", resultados)


# ─────────────────────────────────────────────
# TEST 4 — Retomar conversación y agendar otra cita
# ─────────────────────────────────────────────

def test_retomar_conversacion(orch, db):
    """
    Simula una conversación completa, luego la retoma
    en una nueva sesión y agenda una segunda cita.
    """
    reset_cliente(db)

    # --- SESIÓN 1: Primera cita ---
    print(f"\n   {'·'*40}")
    print(f"   📲 SESIÓN 1 — Primera cita")
    print(f"   {'·'*40}")

    pasos_sesion1 = [
        ("hola quiero una cita",       "opciones"),
        ("uñas normales",              "uñas normales"),
        ("el lunes",                   None),   # busca slots
        ("10",                         None),   # intenta confirmar hora
        ("gracias",                    None),   # cierre conversación
    ]
    resultados1 = run_conversation(orch, db, pasos_sesion1)
    for i, r in enumerate(resultados1, 1):
        icono = f"{VERDE}✅{RESET}" if r["ok"] else f"{AMARILLO}〰{RESET}"
        print(f"   {icono} S1-Paso {i}: '{r['msg']}' → {r['respuesta'][:80]}")

    # --- SESIÓN 2: Nueva sesión, misma memoria ---
    print(f"\n   {'·'*40}")
    print(f"   📲 SESIÓN 2 — Retomar y agendar otra cita")
    print(f"   {'·'*40}")

    # Nueva sesión = history vacío (simula nueva conversación)
    pasos_sesion2 = [
        ("hola de nuevo",              None),          # saludo
        ("quiero otra cita",           "uñas"),        # debe recordar servicio
        ("el miércoles",               None),          # nueva fecha
        ("11",                         None),          # nueva hora
    ]

    history2 = []  # historial limpio — nueva sesión
    resultados2 = []
    for msg, esperado in pasos_sesion2:
        respuesta, history2 = orch.process(db, TEST_PHONE, msg, history2)
        ok = (esperado.lower() in respuesta.lower()) if esperado else True
        resultados2.append({
            "msg":       msg,
            "respuesta": respuesta,
            "esperado":  esperado,
            "ok":        ok
        })
        icono = f"{VERDE}✅{RESET}" if ok else f"{ROJO}❌{RESET}"
        print(f"   {icono} S2-Paso {len(resultados2)}: '{msg}' → {respuesta[:80]}")

    # Verificamos que en sesión 2 recuerde el servicio de sesión 1
    todos = resultados1 + resultados2
    ok_count = sum(1 for r in todos if r["ok"])

    # Check específico: sesión 2 debe recordar el servicio sin preguntarlo
    recuerda_servicio = any(
        "uñas" in r["respuesta"].lower()
        for r in resultados2[:2]
    )
    print(f"\n   📋 ¿Recuerda el servicio en sesión 2? {'✅ Sí' if recuerda_servicio else '❌ No'}")

    # Check: metadata_json tras sesión 2
    cliente  = db.query(Client).filter(Client.phone == TEST_PHONE).first()
    meta     = cliente.metadata_json if cliente else {}
    print(f"   📋 metadata_json tras sesión 2: {meta}")

    return imprimir("Retomar conversación + nueva cita", todos)

def main():
    print(f"\n{'='*60}")
    print("🔍 CoreAppointment — Tests de Fallos")
    print(f"{'='*60}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📱 Teléfono: {TEST_PHONE}\n")

    orch = ValeriaMaster()
    db   = SessionLocal()

    total_ok = total = 0
    try:
        for fn in [test_memoria, test_franja, test_antes_sabado, test_retomar_conversacion]:
            ok, t = fn(orch, db)
            total_ok += ok
            total    += t
    except Exception as e:
        import traceback
        print(f"\n{ROJO}❌ Error: {e}{RESET}")
        print(traceback.format_exc())
    finally:
        db.close()

    print(f"\n{'='*60}")
    color = VERDE if total_ok == total else AMARILLO if total_ok > total // 2 else ROJO
    print(f"{color}📊 RESULTADO: {total_ok}/{total} pasos OK{RESET}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()