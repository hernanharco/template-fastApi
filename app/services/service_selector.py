import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.services import Service


class ServiceSelector:

    MIN_SIMILARITY_SCORE = 0.72

    @staticmethod
    def normalize_text(value: str) -> str:
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
        """Devuelve UN solo servicio (comportamiento original)."""
        results = cls.find_services_by_text(
            db=db,
            user_text=user_text,
            shown_service_ids=shown_service_ids,
        )
        return results[0] if results else None

    @classmethod
    def find_services_by_text(
        cls,
        db: Session,
        user_text: str,
        shown_service_ids: Optional[List[int]] = None,
    ) -> List[Service]:
        """
        Devuelve TODOS los servicios que coincidan con el texto del usuario.

        Estrategia:
        1. Si hay match exacto → devolver solo ese
        2. Si hay matches parciales → devolver todos ordenados por score
        3. Si hay fuzzy match único sobre el umbral → devolver ese
        """
        normalized_input = cls.normalize_text(user_text)
        if not normalized_input:
            return []

        services = cls._get_active_services(db=db, shown_service_ids=shown_service_ids)
        if not services:
            return []

        normalized_services = [
            (service, cls.normalize_text(service.name))
            for service in services
        ]

        # 1) Match exacto → resultado único
        for service, normalized_name in normalized_services:
            if normalized_input == normalized_name:
                return [service]

        # 2) Matches parciales → devolver todos
        partial_matches = []
        for service, normalized_name in normalized_services:
            if normalized_input in normalized_name or normalized_name in normalized_input:
                score = cls.similarity(normalized_input, normalized_name)
                partial_matches.append((score, service))

        if partial_matches:
            partial_matches.sort(key=lambda item: item[0], reverse=True)
            return [service for _, service in partial_matches]

        # 3) Fuzzy match → solo si supera el umbral
        best_score = 0.0
        best_service = None
        for service, normalized_name in normalized_services:
            score = cls.similarity(normalized_input, normalized_name)
            if score > best_score:
                best_score = score
                best_service = service

        if best_service and best_score >= cls.MIN_SIMILARITY_SCORE:
            return [best_service]

        return []