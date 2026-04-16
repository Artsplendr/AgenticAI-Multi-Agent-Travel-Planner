"""Tool-based hotel recommendation agent."""

from __future__ import annotations

from typing import Any

from tools.hotel_search import filter_hotels_by_style, search_hotels


class HotelAgent:
    """Uses tool calls for hotel retrieval, filtering, and selection."""

    ALLOWED_BUDGETS = {"low", "medium", "high"}
    ALLOWED_STYLES = {"adventure", "relaxation", "culture", "foodie", "balanced"}

    def run(
        self,
        destination: str,
        days: int,
        budget_tier: str,
        style: str,
        travelers: int | None = None,
        month: str | None = None,
    ) -> dict[str, Any]:
        destination = self._normalize_destination(destination)
        days = self._normalize_days(days)
        budget_tier = self._normalize_budget_tier(budget_tier)
        style = self._normalize_style(style)
        travelers = self._normalize_travelers(travelers)
        month = self._normalize_optional_text(month)

        search_params = {
            "destination": destination,
            "days": days,
            "budget_tier": budget_tier,
            "style": style,
            "travelers": travelers,
            "month": month,
        }

        if destination == "Unknown":
            return {
                "status": "error",
                "reason": "Missing or unknown destination.",
                "search_params": search_params,
                "hotel": None,
                "all_options": [],
                "count": 0,
            }

        try:
            options = search_hotels(
                destination=destination,
                budget_tier=budget_tier,
                travelers=travelers,
                month=month,
            )

            if not options:
                return {
                    "status": "no_results",
                    "reason": "No hotel options found for the given criteria.",
                    "search_params": search_params,
                    "hotel": None,
                    "all_options": [],
                    "count": 0,
                }

            ranked = filter_hotels_by_style(options=options, style=style)

            if not ranked:
                return {
                    "status": "no_results",
                    "reason": "No hotel options remained after style filtering.",
                    "search_params": search_params,
                    "hotel": None,
                    "all_options": [],
                    "count": 0,
                }

            selected = ranked[0]
            nights = days
            total = int(selected["nightly_rate"] * nights)

            hotel = {
                "name": selected["name"],
                "nightly_rate": selected["nightly_rate"],
                "nights": nights,
                "total": total,
                "area": selected["area"],
                "style_match": selected.get("style_match", False),
                "amenities": selected.get("amenities", []),
                "traveler_capacity": selected.get("traveler_capacity"),
                "destination": destination,
                "month": month,
            }

            return {
                "status": "success",
                "reason": None,
                "search_params": search_params,
                "hotel": hotel,
                "all_options": ranked,
                "count": len(ranked),
            }

        except Exception as exc:
            return {
                "status": "error",
                "reason": f"Hotel search failed: {exc}",
                "search_params": search_params,
                "hotel": None,
                "all_options": [],
                "count": 0,
            }

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

    def _normalize_budget_tier(self, value: str | None) -> str:
        budget = str(value or "").strip().lower()
        return budget if budget in self.ALLOWED_BUDGETS else "medium"

    def _normalize_style(self, value: str | None) -> str:
        style = str(value or "").strip().lower()
        return style if style in self.ALLOWED_STYLES else "balanced"

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
    def _normalize_optional_text(value: str | None) -> str | None:
        text = str(value or "").strip()
        return text if text else None