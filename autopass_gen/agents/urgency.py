from __future__ import annotations

import re

from autopass_gen.core.schema import RequestSpec, RouteSpec, UrgencyContext


class RequestUrgencyInterpreter:
    """Small deterministic interpreter: no chatbot needed, but still agentic and auditable."""

    def interpret(self, request: RequestSpec, route: RouteSpec) -> UrgencyContext:
        text = request.text.lower()
        deadline = request.deadline_min or self._extract_minutes(text) or 15.0
        if deadline <= 7 or any(w in text for w in ["urgent", "emergency", "late", "asap"]):
            level = "high"
            cost = 3.0
        elif deadline <= 12:
            level = "medium"
            cost = 1.5
        else:
            level = "low"
            cost = 0.5
        return UrgencyContext(
            start=request.start or route.start,
            goal=request.goal or route.goal,
            deadline_min=deadline,
            urgency_level=level,
            delay_cost=cost,
            parsed_from=request.text,
        )

    @staticmethod
    def _extract_minutes(text: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:min|minute|minutes)", text)
        return float(match.group(1)) if match else None
