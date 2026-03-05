import pytest
from app.agents.routing.rules import evaluate_all_rules

class TestRoutingRules:
    """
    🎯 SRP: Probar exclusivamente la lógica de decisión de rules.py.
    """

    def test_greeting_new_client(self):
        """Debe retornar GREETING si el usuario saluda y es nuevo."""
        user_input = "Hola, qué tal"
        current_name = "Nuevo Cliente"
        
        action, selected_id = evaluate_all_rules(user_input, current_name, [], [])
        
        assert action == "GREETING"
        assert selected_id is None

    def test_catalog_returning_client(self):
        """Debe retornar CATALOG si el usuario saluda pero ya lo conocemos."""
        user_input = "Buenas"
        current_name = "Hernan"
        
        action, selected_id = evaluate_all_rules(user_input, current_name, [], [])
        
        assert action == "CATALOG"

    def test_normalization_time_with_dot(self):
        """
        🚀 EL TEST CLAVE:
        Debe entender '11.00' como una confirmación si existe el slot '11:00'.
        """
        user_input = "11.00"
        active_slots = [{"time": "11:00"}, {"time": "12:00"}]
        
        action, selected_id = evaluate_all_rules(user_input, "Hernan", [], active_slots)
        
        assert action == "CONFIRMATION"

    def test_selection_by_index_service(self):
        """Debe permitir elegir el servicio por número (ej: 'la 1')."""
        user_input = "la 1"
        shown_ids = [10, 20, 30] # IDs de la DB
        
        # Simulamos que no hay slots aún (estamos en el catálogo)
        action, selected_id = evaluate_all_rules(user_input, "Hernan", shown_ids, [])
        
        assert action == "BOOKING"
        assert selected_id == 10

    def test_temporal_rule_day(self):
        """Debe detectar si el usuario pide un día específico."""
        user_input = "quiero para mañana"
        
        action, selected_id = evaluate_all_rules(user_input, "Hernan", [], [])
        
        assert action == "BOOKING"

#poetry run pytest tests/test_routing_rules.py -v