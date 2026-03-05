# app/agents/shared/name_extractor.py
"""
SRP: Extractor de Nombres de Cliente
Responsabilidad única: Extraer nombres propios de mensajes de usuario con alta precisión
"""
import re
from typing import Optional, Tuple
from pydantic import BaseModel, Field, validator
from rich.console import Console

console = Console()


class NameExtractionResult(BaseModel):
    """Resultado de la extracción de nombre"""

    name: Optional[str] = Field(
        None, description="Nombre extraído o None si no se detecta"
    )
    confidence: float = Field(0.0, description="Confianza de la extracción (0.0-1.0)")
    method: str = Field(..., description="Método usado para la extracción")

    @validator("confidence")
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confianza debe estar entre 0.0 y 1.0")
        return v


class NameExtractor:
    """Extractor especializado de nombres propios"""

    def __init__(self):
        # Patrones de extracción de nombres
        self.name_patterns = [
            # Patrones explícitos
            (r"me llamo\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+)", 0.9),
            (r"mi nombre es\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+)", 0.9),
            (r"soy\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+)", 0.8),
            (r"nombre es\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+)", 0.8),
            (r"llámame\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+)", 0.7),
            (r"mi nombre\s+es\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+)", 0.8),
            (r"yo soy\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+)", 0.8),
        ]

        # Palabras comunes que NO son nombres
        self.exclude_words = {
            "ok",
            "bien",
            "hola",
            "adios",
            "gracias",
            "por favor",
            "favor",
            "si",
            "no",
            "tal vez",
            "quizás",
            "necesito",
            "quiero",
            "me gustaría",
            "cita",
            "turno",
            "agendar",
            "reserva",
            "servicio",
            "información",
            "hoy",
            "mañana",
            "lunes",
            "martes",
            "miércoles",
            "jueves",
            "viernes",
        }

    def _is_context_name_request(self, messages) -> bool:
        """
        Verifica si el contexto anterior fue una solicitud de nombre
        """
        if not messages:
            return False

        # Buscar en los últimos 3 mensajes si hubo solicitud de nombre
        recent_messages = messages[-3:] if len(messages) >= 3 else messages

        name_request_keywords = [
            "¿cuál es tu nombre",
            "cual es tu nombre",
            "dime tu nombre",
            "¿cómo te llamas",
            "como te llamas",
            "tu nombre es",
            "decime tu nombre",
            "podrías decirme tu nombre",
            "necesito tu nombre",
        ]

        for msg in recent_messages:
            if hasattr(msg, "content"):
                content = msg.content.lower()
                for keyword in name_request_keywords:
                    if keyword in content:
                        console.print(
                            f"[dim]🔍 Detectada solicitud de nombre: '{keyword}'[/dim]"
                        )
                        return True

        return False

    def _extract_with_patterns(self, text: str) -> Tuple[Optional[str], float, str]:
        """
        Extrae nombre usando patrones regex
        """
        text_lower = text.lower().strip()

        for pattern, confidence in self.name_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                name = match.group(1).strip().title()
                if len(name) >= 2 and name.lower() not in self.exclude_words:
                    console.print(
                        f"[dim]🎯 Patrón detectado: {pattern} -> '{name}' (confianza: {confidence})[/dim]"
                    )
                    return name, confidence, f"regex_pattern"

        return None, 0.0, "no_pattern"

    def _extract_contextual_name(
        self, text: str, messages
    ) -> Tuple[Optional[str], float, str]:
        """
        Extrae nombre basado en contexto (respuesta a solicitud de nombre)
        """
        if not self._is_context_name_request(messages):
            return None, 0.0, "no_context"

        text_clean = text.strip()

        # Si el texto es una pregunta, no es un nombre
        question_indicators = ["¿", "?", "cuál", "cual", "nombre", "llamas"]
        if any(indicator in text_clean.lower() for indicator in question_indicators):
            return None, 0.0, "is_question"

        # Si es una sola palabra y no está en excluidos
        if " " not in text_clean and len(text_clean) >= 2:
            if text_clean.lower() not in self.exclude_words:
                name = text_clean.title()
                console.print(
                    f"[dim]🎯 Nombre contextual: '{name}' (confianza: 0.95)[/dim]"
                )
                return name, 0.95, "contextual_single_word"

        # Si son múltiples palabras, podría ser nombre completo
        words = text_clean.split()
        if 2 <= len(words) <= 4:  # Nombre completo típico
            if all(word.lower() not in self.exclude_words for word in words):
                name = " ".join([w.title() for w in words])
                console.print(
                    f"[dim]🎯 Nombre contextual completo: '{name}' (confianza: 0.9)[/dim]"
                )
                return name, 0.9, "contextual_full_name"

        return None, 0.0, "contextual_no_match"

    def extract_name(self, text: str, messages=None) -> NameExtractionResult:
        """
        Extrae nombre del texto usando múltiples estrategias

        Args:
            text: Texto del usuario
            messages: Historial de mensajes para contexto

        Returns:
            NameExtractionResult con el nombre extraído y confianza
        """
        console.print(f"[dim]🔍 Analizando texto para nombre: '{text}'[/dim]")

        # Estrategia 1: Patrones explícitos
        name, confidence, method = self._extract_with_patterns(text)

        # Estrategia 2: Contextual (respuesta a solicitud)
        if not name and messages:
            name, confidence, method = self._extract_contextual_name(text, messages)

        # Estrategia 3: Heurística simple (último recurso)
        if not name:
            text_clean = text.strip()
            if len(text_clean) >= 2 and len(text_clean) <= 30:
                if text_clean.lower() not in self.exclude_words:
                    # Si parece un nombre (empieza con mayúscula)
                    if text_clean[0].isupper():
                        name = text_clean.title()
                        confidence = 0.4
                        method = "heuristic_capitalized"
                        console.print(
                            f"[dim]🎯 Heurística: '{name}' (confianza: {confidence})[/dim]"
                        )

        result = NameExtractionResult(name=name, confidence=confidence, method=method)

        console.print(f"[dim]📊 Resultado extracción: {result}[/dim]")
        return result


# Instancia global para uso en la aplicación
name_extractor = NameExtractor()
