"""Hybrid budget optimization agent (rules + optional LLM refinement)."""

from __future__ import annotations

from typing import Any

from tools.llm_tool import LLMTool, LLMToolError


class BudgetOptimizerAgent:
    """Uses deterministic cost estimation plus optional LLM refinement notes."""

    _TARGET_BY_TIER = {"low": 900, "medium": 1800, "high": 3500}
    _ACTIVITY_UNIT_COST = {"low": 20, "medium": 35, "high": 60}
    _ALLOWED_BUDGETS = {"low", "medium", "high"}
    _ALLOWED_STYLES = {"adventure", "relaxation", "culture", "foodie", "balanced"}

    def __init__(self, llm: LLMTool | None = None) -> None:
        self.llm = llm or LLMTool()

    def run(
        self,
        budget_tier: str,
        days: int,
        flight_price: int,
        hotel_total: int,
        activity_count: int,
        destination: str,
        style: str,
        travelers: int | None = None,
    ) -> dict[str, Any]:
        budget_tier = self._normalize_budget_tier(budget_tier)
        days = self._normalize_days(days)
        flight_price = self._normalize_nonnegative_int(flight_price)
        hotel_total = self._normalize_nonnegative_int(hotel_total)
        activity_count = self._normalize_nonnegative_int(activity_count)
        destination = self._normalize_destination(destination)
        style = self._normalize_style(style)
        travelers = self._normalize_travelers(travelers)

        budget_target = self._TARGET_BY_TIER[budget_tier]
        activity_unit_cost = self._ACTIVITY_UNIT_COST[budget_tier]

        activities_cost = activity_count * activity_unit_cost
        total_cost = flight_price + hotel_total + activities_cost
        over_budget = max(0, total_cost - budget_target)
        within_budget = total_cost <= budget_target

        adjustments: list[str] = []

        if within_budget:
            adjustments.append("Plan is currently within budget.")
            optimized_activities_cost = activities_cost
            optimized_total_cost = total_cost
        else:
            adjustments.append(f"Current estimate exceeds budget by ${over_budget}.")
            adjustments.extend(
                self._rule_based_adjustments(
                    budget_tier=budget_tier,
                    activity_count=activity_count,
                    flight_price=flight_price,
                    hotel_total=hotel_total,
                )
            )

            reduced_activity_count = max(0, activity_count - 1)
            optimized_activities_cost = reduced_activity_count * activity_unit_cost
            optimized_total_cost = flight_price + hotel_total + optimized_activities_cost

        llm_suggestion = self._generate_suggestion(
            destination=destination,
            style=style,
            budget_tier=budget_tier,
            days=days,
            target=budget_target,
            total=optimized_total_cost,
            travelers=travelers,
        )
        if llm_suggestion:
            adjustments.append(llm_suggestion)

        return {
            "status": "success",
            "reason": None,
            "budget_target": budget_target,
            "currency": "USD",
            "days": days,
            "travelers": travelers,
            "cost_breakdown": {
                "flight": flight_price,
                "hotel": hotel_total,
                "activities": optimized_activities_cost,
            },
            "activity_unit_cost": activity_unit_cost,
            "activity_count": activity_count,
            "estimated_total": optimized_total_cost,
            "is_within_budget": optimized_total_cost <= budget_target,
            "over_under_amount": budget_target - optimized_total_cost,
            "adjustments": adjustments,
        }

    def _generate_suggestion(
        self,
        destination: str,
        style: str,
        budget_tier: str,
        days: int,
        target: int,
        total: int,
        travelers: int | None,
    ) -> str:
        try:
            parsed = self.llm.complete_json(
                system_prompt=(
                    "You are a travel budget optimizer. "
                    "Return only JSON with key 'suggestion' containing one practical sentence. "
                    "The suggestion should be realistic, concise, and aligned with the travel style."
                ),
                user_prompt=(
                    f"Destination: {destination}\n"
                    f"Style: {style}\n"
                    f"Budget tier: {budget_tier}\n"
                    f"Days: {days}\n"
                    f"Travelers: {travelers if travelers is not None else 'Unknown'}\n"
                    f"Target budget: {target}\n"
                    f"Current estimate: {total}\n"
                    "Provide one practical optimization suggestion."
                ),
            )
            suggestion = str(parsed.get("suggestion", "")).strip()
            return suggestion if suggestion else ""
        except (LLMToolError, TypeError, ValueError, AttributeError):
            return ""

    @staticmethod
    def _rule_based_adjustments(
        budget_tier: str,
        activity_count: int,
        flight_price: int,
        hotel_total: int,
    ) -> list[str]:
        notes: list[str] = []

        if activity_count > 0:
            notes.append("Reduce one paid activity to lower the daily experience cost.")

        if budget_tier == "low":
            notes.append("Favor the cheapest acceptable flight and simple central lodging.")
        elif budget_tier == "medium":
            notes.append("Keep a balanced hotel choice and avoid premium add-ons.")
        else:
            notes.append("Preserve comfort while trimming non-essential premium extras.")

        if hotel_total > flight_price:
            notes.append("Hotel cost is the larger driver, so consider a slightly lower room category.")
        else:
            notes.append("Flight cost is a major driver, so prioritize the most cost-effective routing.")

        return notes

    def _normalize_budget_tier(self, value: str | None) -> str:
        budget = str(value or "").strip().lower()
        if budget in self._ALLOWED_BUDGETS:
            return budget

        synonyms = {
            "cheap": "low",
            "budget": "low",
            "economy": "low",
            "affordable": "low",
            "mid": "medium",
            "midrange": "medium",
            "mid-range": "medium",
            "moderate": "medium",
            "luxury": "high",
            "premium": "high",
            "upscale": "high",
        }
        return synonyms.get(budget, "medium")

    def _normalize_style(self, value: str | None) -> str:
        style = str(value or "").strip().lower()
        if style in self._ALLOWED_STYLES:
            return style

        synonyms = {
            "relaxed": "relaxation",
            "relaxing": "relaxation",
            "cultural": "culture",
            "history": "culture",
            "historical": "culture",
            "food": "foodie",
            "culinary": "foodie",
        }
        return synonyms.get(style, "balanced")

    @staticmethod
    def _normalize_days(value: int | None) -> int:
        try:
            days = int(value)
            return max(1, min(30, days))
        except (TypeError, ValueError):
            return 5

    @staticmethod
    def _normalize_nonnegative_int(value: int | None) -> int:
        try:
            parsed = int(value)
            return max(0, parsed)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _normalize_destination(value: str | None) -> str:
        text = str(value or "").strip()
        return text if text else "Unknown"

    @staticmethod
    def _normalize_travelers(value: int | None) -> int | None:
        if value is None:
            return None
        try:
            travelers = int(value)
            return travelers if travelers > 0 else None
        except (TypeError, ValueError):
            return None