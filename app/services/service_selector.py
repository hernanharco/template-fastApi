# app/services/service_selector.py

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.services import Service


class ServiceSelector:
    """
    Resuelve el texto del usuario a un servicio activo.

    Responsabilidad:
    - Normalizar texto
    - Buscar coincidencia exacta, parcial o aproximada
    - Priorizar servicios mostrados previamente si aplica
    """

    MIN_SIMILARITY_SCORE = 0.72

    @staticmethod
    def normalize_text(value: str) -> str:
        """
        Normaliza texto para comparar:
        - minúsculas
        - sin tildes
        - sin símbolos extra
        - espacios compactados
        """
        if not value:
            return ""

        value = value.strip().lower()
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @classmethod
    def similarity(cls, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    @classmethod
    def _get_active_services(
        cls,
        db: Session,
        shown_service_ids: Optional[List[int]] = None,
    ) -> List[Service]:
        query = db.query(Service).filter(Service.is_active == True)

        # Si el catálogo reciente existe, intentamos priorizarlo
        if shown_service_ids:
            prioritized = (
                query.filter(Service.id.in_(shown_service_ids))
                .order_by(Service.name.asc())
                .all()
            )
            if prioritized:
                return prioritized

        return query.order_by(Service.name.asc()).all()

    @classmethod
    def find_service_by_text(
        cls,
        db: Session,
        user_text: str,
        shown_service_ids: Optional[List[int]] = None,
    ) -> Optional[Service]:
        """
        Busca el mejor match de servicio a partir del texto del usuario.

        Estrategia:
        1. exact match normalizado
        2. contains match
        3. fuzzy match
        """
        normalized_input = cls.normalize_text(user_text)
        if not normalized_input:
            return None

        services = cls._get_active_services(
            db=db,
            shown_service_ids=shown_service_ids,
        )

        if not services:
            return None

        normalized_services = []
        for service in services:
            normalized_name = cls.normalize_text(service.name)
            normalized_services.append((service, normalized_name))

        # 1) Match exacto
        for service, normalized_name in normalized_services:
            if normalized_input == normalized_name:
                return service

        # 2) Match parcial
        partial_matches = []
        for service, normalized_name in normalized_services:
            if normalized_input in normalized_name or normalized_name in normalized_input:
                score = cls.similarity(normalized_input, normalized_name)
                partial_matches.append((score, service))

        if partial_matches:
            partial_matches.sort(key=lambda item: item[0], reverse=True)
            return partial_matches[0][1]

        # 3) Fuzzy match
        best_score = 0.0
        best_service = None

        for service, normalized_name in normalized_services:
            score = cls.similarity(normalized_input, normalized_name)
            if score > best_score:
                best_score = score
                best_service = service

        if best_service and best_score >= cls.MIN_SIMILARITY_SCORE:
            return best_service

        return None