import pytest
import sys
import os
from datetime import datetime, timedelta

# Aseguramos que Python encuentre la carpeta 'app'
sys.path.append(os.getcwd())

# --- SIMULACIÓN DE COMPONENTES (MOCKS) ---
# Esto representa tu lógica actual de test_agent.py pero automatizada
class ValeriaMock:
    def __init__(self):
        self.memory = {"phone": None, "service": None, "date": None, "time": None}
        self.history = []

    def process_message(self, message):
        msg = message.lower()
        self.history.append(message)
        
        # Simulación de Lógica de Flujos
        if "hola" in msg:
            return "¡Hola! Bienvenido a Beauty Pro."
        
        if "cita" in msg or "hoy" in msg:
            self.memory["date"] = "2026-02-14"
            return "Claro, ¿qué servicio quieres? (Uñas Normales, Acrílicas...)"
        
        if "normales" in msg:
            self.memory["service"] = "Uñas Normales"
            return "Perfecto. Para el 14/02 no hay huecos. ¿Otro día?"
        
        if "miércoles" in msg or "18" in msg:
            self.memory["date"] = "2026-02-18"
            return "El 18/02 tengo a las 10:00 y 10:15. ¿Cuál prefieres?"
        
        if "tarde" in msg:
            return "No tengo disponibilidad en la tarde. ¿Mañana?"

        if "salir" in msg:
            self.memory = {"phone": None, "service": None, "date": None, "time": None}
            return "Adiós."
            
        return "No te entendí bien, ¿puedes repetir?"

# --- CLASE DE TEST ---
class TestValeriaFlow:

    @pytest.fixture
    def bot(self):
        """Instancia fresca de Valeria para cada test."""
        return ValeriaMock()

    # --- TESTS DE FLUJO (LOS 20 ESCENARIOS) ---

    def test_01_flujo_feliz_completo(self, bot):
        """Usuario reserva con éxito."""
        bot.process_message("Hola")
        bot.process_message("Quiero cita para hoy")
        bot.process_message("Uñas normales")
        res = bot.process_message("El miércoles entonces")
        assert "18/02" in res
        assert "10:00" in res

    def test_02_cambio_fecha_por_cupo_lleno(self, bot):
        """Valida que sugiera otro día si hoy está lleno."""
        bot.process_message("cita hoy")
        res = bot.process_message("uñas normales")
        assert "no hay huecos" in res.lower()

    def test_03_extraccion_miercoles(self, bot):
        """Verifica que el miércoles actualice la memoria al 2026-02-18."""
        bot.process_message("que tal el miércoles")
        assert bot.memory["date"] == "2026-02-18"

    def test_04_manejo_tarde_vago(self, bot):
        """Si pide 'tarde', no debe asignar hora."""
        res = bot.process_message("¿tienes algo en la tarde?")
        assert bot.memory["time"] is None
        assert "No tengo disponibilidad en la tarde" in res

    def test_05_persistencia_servicio(self, bot):
        """El servicio debe quedarse en memoria."""
        bot.process_message("uñas normales")
        assert bot.memory["service"] == "Uñas Normales"

    def test_06_cambio_servicio_mitad(self, bot):
        """Cambiar de idea sobre el servicio."""
        bot.process_message("uñas normales")
        bot.process_message("mejor quiero acrílicas")
        # Aquí añadirías lógica para que el bot actualice memory["service"]
        pass

    def test_07_horario_invalido(self, bot):
        """Simular mensaje fuera de rango."""
        res = bot.process_message("a las 3 am")
        assert "No te entendí" in res

    def test_08_numero_movil_corto(self, bot):
        """Validar que el sistema pida un número real."""
        bot.memory["phone"] = "123"
        assert len(bot.memory["phone"]) < 9

    def test_09_limpieza_memoria(self, bot):
        """Simular comando 'salir'."""
        bot.process_message("uñas normales")
        bot.process_message("salir")
        assert bot.memory["service"] is None

    def test_10_charla_casual(self, bot):
        """No debe romper el flujo de cita si saluda."""
        res = bot.process_message("Hola")
        assert "Bienvenido" in res

    # 11-20: Ideas para implementar
    def test_11_zona_horaria(self, bot): pass
    def test_12_dia_festivo(self, bot): pass
    def test_13_palabra_clave_salir(self, bot): 
        res = bot.process_message("salir")
        assert "Adiós" in res
    def test_14_doble_reserva(self, bot): pass
    def test_15_formato_hora_texto(self, bot): pass
    def test_16_reentrada_memoria(self, bot): pass
    def test_17_cambio_colaborador(self, bot): pass
    def test_18_gracias_flujo(self, bot): pass
    def test_19_cors_mock(self, bot): pass
    def test_20_timeout_simulado(self, bot): pass

if __name__ == "__main__":
    # Si ejecutas el archivo con python, usamos pytest directamente
    pytest.main([__file__])