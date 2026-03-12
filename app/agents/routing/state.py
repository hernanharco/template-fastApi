from datetime import date, datetime
from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict

from app.agents.routing.intent import Intent


class RoutingState(TypedDict, total=False):

    # 1) Conversation memory
    messages: List[Dict[str, Any]]
    memories: Optional[str]

    # 2) User data
    client_phone: str
    client_name: Optional[str]
    client_id: Optional[int]
    is_new_user: bool
    preferred_collaborators: List[int]

    # 3) Flow control
    intent: Optional[Intent]
    next_action: Optional[str]
    force_greeting: bool
    wait_for_name: bool
    response_text: Optional[str]

    # 4) Catalog memory
    shown_service_ids: List[int]
    selected_service_id: Optional[int]
    service_candidates: List[Dict[str, Any]]  # ← NUEVO: candidatos ambiguos

    # 5) Temporal data
    selected_date: Optional[date]
    time_filter: Optional[Dict[str, Any]]
    selection_preference: Optional[str]

    # 6) Booking memory
    active_slots: List[Dict[str, Any]]
    selected_collaborator_id: Optional[int]
    selected_datetime: Optional[datetime]
    booking_for_name: Optional[str]
    other_day_attempts: int

    # 7) Confirmation/result
    appointment_id: Optional[int]
    booking_confirmed: bool