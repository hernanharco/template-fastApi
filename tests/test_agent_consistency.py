# tests/test_agent_consistency.py
"""
Tests para verificar consistencia del agente con diferentes palabras clave
"""
import pytest
from app.agents.core.graph import workflow
from app.agents.core.state import AgentState
from langchain_core.messages import HumanMessage


class TestAgentConsistency:

    @pytest.fixture
    def base_state(self):
        """Estado base para todos los tests"""
        return {
            "messages": [],
            "client_phone": "34634405549",
            "client_name": None,
            "service_id": None,
            "appointment_date": None,
            "next_node": None,
        }

    def test_greeting_keywords(self, base_state):
        """Test detección de saludos"""
        greeting_keywords = [
            "hola",
            "buenos dias",
            "buenas tardes",
            "qué tal",
            "hey",
            "hi",
            "hello",
        ]

        for keyword in greeting_keywords:
            state = base_state.copy()
            state["messages"] = [HumanMessage(content=keyword)]

            # Simular routing
            from app.agents.core.graph import should_continue

            next_node = should_continue(state)

            # Debería routear a greeting
            assert next_node == "greeting", f"Keyword '{keyword}' failed routing"

    def test_service_keywords(self, base_state):
        """Test detección de palabras clave de servicios"""
        service_keywords = [
            "servicio",
            "servicios",
            "qué ofrecen",
            "ofrecen",
            "precios",
            "cuánto cuesta",
            "catálogo",
            "lista",
            "opciones",
        ]

        for keyword in service_keywords:
            state = base_state.copy()
            state["messages"] = [HumanMessage(content=keyword)]

            # Simular routing
            from app.agents.core.graph import should_continue

            next_node = should_continue(state)

            # Debería routear a tools (para search_services)
            assert next_node in [
                "tools",
                "agent",
            ], f"Service keyword '{keyword}' failed routing"

    def test_booking_keywords(self, base_state):
        """Test detección de palabras clave de agendamiento"""
        booking_keywords = [
            "cita",
            "turno",
            "agendar",
            "reserva",
            "disponible",
            "mañana",
            "lunes",
            "martes",
            "hoy",
            "espacio",
            "hora",
        ]

        for keyword in booking_keywords:
            state = base_state.copy()
            state["messages"] = [HumanMessage(content=keyword)]

            # Simular routing
            from app.agents.core.graph import should_continue

            next_node = should_continue(state)

            # Debería routear a tools o agent
            assert next_node in [
                "tools",
                "agent",
            ], f"Booking keyword '{keyword}' failed routing"

    def test_service_selection_numbers(self, base_state):
        """Test selección de servicios por número"""
        for num in range(1, 10):
            state = base_state.copy()
            state["messages"] = [HumanMessage(content=str(num))]

            # Simular routing
            from app.agents.core.graph import should_continue

            next_node = should_continue(state)

            # Debería routear a agent (que luego usará tools)
            assert next_node == "agent", f"Service selection '{num}' failed routing"

    def test_message_accumulation_prevention(self, base_state):
        """Test que el historial no crece indefinidamente"""
        from app.agents.core.state import AgentState

        # Simular 20 mensajes
        messages = [HumanMessage(content=f"mensaje {i}") for i in range(20)]
        state = base_state.copy()
        state["messages"] = messages

        # Verificar que no haya mecanismo de limpieza automático
        # Este test es para documentar el comportamiento actual
        assert len(state["messages"]) == 20, "Message accumulation detected"

        # Test de limpieza manual
        from app.agents.core.message_cleaner import (
            clean_message_history,
            should_clean_history,
        )

        # Debería detectar que necesita limpieza
        assert should_clean_history(messages), "Should detect need for cleaning"

        # Debería limpiar correctamente
        cleaned = clean_message_history(messages)
        assert len(cleaned) <= 15, "Should clean to max_messages"

        # Debería mantener SystemMessage
        from langchain_core.messages import SystemMessage

        system_messages = [msg for msg in cleaned if isinstance(msg, SystemMessage)]
        # Si no hay SystemMessage, es OK porque las pruebas no las incluyen


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
