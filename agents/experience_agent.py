"""LLM-assisted experience recommendation agent."""

from __future__ import annotations

from typing import Any

from tools.activity_search import build_itinerary_fallback, search_activities
from tools.llm_tool import LLMTool, LLMToolError


class ExperienceAgent:
    """Generates activities and a day-by-day itinerary.

    Uses an LLM when available for richer personalization and falls back to
    deterministic activity generation when the LLM is unavailable or returns
    invalid output.
    """

    ALLOWED_STYLES = {"adventure", "relaxation", "culture", "foodie", "balanced"}

    def __init__(self, llm: LLMTool | None = None) -> None:
        self.llm = llm or LLMTool()

    def run(
        self,
        destination: str,
        days: int,
        style: str,
        month: str | None = None,
        travelers: int | None = None,
    ) -> dict[str, Any]:
        destination = self._normalize_destination(destination)
        days = self._normalize_days(days)
        style = self._normalize_style(style)
        month = self._normalize_optional_text(month)
        travelers = self._normalize_travelers(travelers)

        search_params = {
            "destination": destination,
            "days": days,
            "style": style,
            "month": month,
            "travelers": travelers,
        }

        if destination == "Unknown":
            return {
                "status": "error",
                "reason": "Missing or unknown destination.",
                "search_params": search_params,
                "activities": [],
                "itinerary": [],
                "count": 0,
                "source": "none",
            }

        llm_plan = self._try_llm_experience(
            destination=destination,
            days=days,
            style=style,
            month=month,
            travelers=travelers,
        )

        if llm_plan is not None:
            activities = self._normalize_activities(llm_plan.get("activities"))
            itinerary = self._normalize_itinerary(llm_plan.get("itinerary"), days=days)

            if activities and itinerary:
                return {
                    "status": "success",
                    "reason": None,
                    "search_params": search_params,
                    "activities": activities,
                    "itinerary": itinerary,
                    "count": len(activities),
                    "source": "llm",
                }

        activities = search_activities(
            destination=destination,
            style=style,
            month=month,
            travelers=travelers,
        )
        itinerary = build_itinerary_fallback(
            destination=destination,
            activities=activities,
            days=days,
            style=style,
        )

        return {
            "status": "success",
            "reason": "Used deterministic fallback because LLM output was unavailable or invalid.",
            "search_params": search_params,
            "activities": activities,
            "itinerary": itinerary,
            "count": len(activities),
            "source": "fallback",
        }

    def _try_llm_experience(
        self,
        destination: str,
        days: int,
        style: str,
        month: str | None,
        travelers: int | None,
    ) -> dict[str, Any] | None:
        try:
            parsed = self.llm.complete_json(
                system_prompt=(
                    "You are a travel experience planner. "
                    "Return only JSON with keys: "
                    "activities (list of short strings) and "
                    "itinerary (list of day-by-day strings). "
                    "Keep itinerary length exactly equal to the requested number of days. "
                    "Suggestions must be realistic, varied, and aligned with the user's travel style. "
                    "Do not include extra keys."
                ),
                user_prompt=(
                    f"Destination: {destination}\n"
                    f"Days: {days}\n"
                    f"Style: {style}\n"
                    f"Month: {month or 'Unknown'}\n"
                    f"Travelers: {travelers if travelers is not None else 'Unknown'}\n"
                    "Create engaging but realistic activities and a day-by-day itinerary."
                ),
            )
            return parsed if isinstance(parsed, dict) else None
        except (LLMToolError, TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _normalize_destination(value: str | None) -> str:
        text = str(value or "").strip()
        return text if text else "Unknown"

    @staticmethod
    def _normalize_days(value: int | None) -> int:
        try:
            days = int(value)
            return max(1, min(30, days))
        except (TypeError, ValueError):
            return 5

    def _normalize_style(self, value: str | None) -> str:
        style = str(value or "").strip().lower()
        return style if style in self.ALLOWED_STYLES else "balanced"

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        text = str(value or "").strip()
        return text if text else None

    @staticmethod
    def _normalize_travelers(value: int | None) -> int | None:
        if value is None:
            return None
        try:
            travelers = int(value)
            return travelers if travelers > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_activities(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        normalized: list[str] = []
        seen: set[str] = set()

        for item in value:
            text = str(item).strip()
            if not text:
                continue
            if text.lower() in seen:
                continue
            seen.add(text.lower())
            normalized.append(text)

        return normalized

    @staticmethod
    def _normalize_itinerary(value: Any, days: int) -> list[str]:
        if not isinstance(value, list):
            return []

        normalized = [str(item).strip() for item in value if str(item).strip()]
        if len(normalized) != days:
            return []

        return normalized