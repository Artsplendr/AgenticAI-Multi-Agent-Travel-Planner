"""LLM-first aggregation agent for final traveler response."""

from __future__ import annotations

from typing import Any

from tools.llm_tool import LLMTool, LLMToolError


class AggregatorAgent:
    """Combines agent outputs into a traveler-friendly final response."""

    def __init__(self, llm: LLMTool | None = None) -> None:
        self.llm = llm or LLMTool()

    def run(
        self,
        destination: str,
        original_prompt: str,
        intent: dict[str, Any],
        flight_data: dict[str, Any],
        hotel_data: dict[str, Any],
        experience_data: dict[str, Any],
        budget_data: dict[str, Any],
    ) -> dict[str, Any]:
        destination = self._normalize_destination(destination)
        intent = intent if isinstance(intent, dict) else {}
        flight_data = flight_data if isinstance(flight_data, dict) else {}
        hotel_data = hotel_data if isinstance(hotel_data, dict) else {}
        experience_data = experience_data if isinstance(experience_data, dict) else {}
        budget_data = budget_data if isinstance(budget_data, dict) else {}

        best_flight = flight_data.get("best_option")
        hotel = hotel_data.get("hotel")
        activities = self._normalize_str_list(experience_data.get("activities"))
        itinerary = self._normalize_str_list(experience_data.get("itinerary"))

        budget = {
            "target": budget_data.get("budget_target"),
            "estimated_total": budget_data.get("estimated_total"),
            "currency": budget_data.get("currency", "USD"),
            "is_within_budget": budget_data.get("is_within_budget"),
            "over_under_amount": budget_data.get("over_under_amount"),
            "notes": self._normalize_str_list(budget_data.get("adjustments")),
            "cost_breakdown": budget_data.get("cost_breakdown", {}),
        }

        result = {
            "status": "success",
            "reason": None,
            "destination": destination,
            "intent": intent,
            "flight": best_flight,
            "hotel": hotel,
            "activities": activities,
            "itinerary": itinerary,
            "budget": budget,
            "agent_statuses": {
                "flight": flight_data.get("status"),
                "hotel": hotel_data.get("status"),
                "experience": experience_data.get("status"),
                "budget": budget_data.get("status"),
            },
            "missing_components": self._collect_missing_components(
                flight=best_flight,
                hotel=hotel,
                activities=activities,
                itinerary=itinerary,
            ),
        }

        result["trip_summary"] = self._generate_trip_summary(
            original_prompt=original_prompt,
            plan=result,
        )

        return result

    def _generate_trip_summary(self, original_prompt: str, plan: dict[str, Any]) -> str:
        try:
            parsed = self.llm.complete_json(
                system_prompt=(
                    "You summarize travel plans. "
                    "Return only JSON with key 'summary' containing 2-3 concise sentences. "
                    "Mention the destination, trip length, travel style, and one practical highlight."
                ),
                user_prompt=(
                    f"User request: {original_prompt}\n"
                    f"Structured plan: {plan}\n"
                    "Write a clear traveler-friendly summary."
                ),
            )
            summary = str(parsed.get("summary", "")).strip()
            if summary:
                return summary
        except (LLMToolError, TypeError, ValueError, AttributeError):
            pass

        return self._fallback_summary(plan)

    def _fallback_summary(self, plan: dict[str, Any]) -> str:
        destination = plan.get("destination", "this destination")
        intent = plan.get("intent", {}) or {}
        days = intent.get("days", "several")
        style = intent.get("style", "balanced")
        budget_tier = intent.get("budget_tier", "medium")

        hotel = plan.get("hotel") or {}
        hotel_name = hotel.get("name")

        flight = plan.get("flight") or {}
        airline = flight.get("airline")

        parts = [
            f"This plan outlines a {days}-day trip to {destination} tailored to a {style} travel style and a {budget_tier} budget."
        ]

        if airline:
            parts.append(f"The recommended flight option is with {airline}.")

        if hotel_name:
            parts.append(f"The selected stay is {hotel_name}.")

        return " ".join(parts)

    @staticmethod
    def _collect_missing_components(
        flight: dict[str, Any] | None,
        hotel: dict[str, Any] | None,
        activities: list[str],
        itinerary: list[str],
    ) -> list[str]:
        missing: list[str] = []

        if not flight:
            missing.append("flight")
        if not hotel:
            missing.append("hotel")
        if not activities:
            missing.append("activities")
        if not itinerary:
            missing.append("itinerary")

        return missing

    @staticmethod
    def _normalize_destination(value: str | None) -> str:
        text = str(value or "").strip()
        return text if text else "Unknown"

    @staticmethod
    def _normalize_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized