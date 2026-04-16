"""Tool-based flight search agent."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from tools.flight_search import search_flights, select_best_flight


class FlightAgent:
    """Uses dedicated search/ranking tools for flight planning."""

    ALLOWED_BUDGETS = {"low", "medium", "high"}

    def run(
        self,
        destination: str,
        budget_tier: str,
        origin: str | None = None,
        month: str | None = None,
        travelers: int | None = None,
        days: int | None = None,
    ) -> dict[str, Any]:
        destination = self._normalize_destination(destination)
        budget_tier = self._normalize_budget_tier(budget_tier)
        origin = self._normalize_optional_text(origin)
        month = self._normalize_optional_text(month)
        travelers = self._normalize_travelers(travelers)
        days = self._normalize_days(days)

        search_params = {
            "destination": destination,
            "budget_tier": budget_tier,
            "origin": origin,
            "month": month,
            "travelers": travelers,
            "days": days,
        }

        if destination == "Unknown":
            return {
                "status": "error",
                "reason": "Missing or unknown destination.",
                "search_params": search_params,
                "best_option": None,
                "all_options": [],
                "count": 0,
            }

        try:
            raw_options = search_flights(
                destination=destination,
                budget_tier=budget_tier,
                origin=origin,
                month=month,
                travelers=travelers,
                days=days,
            )
            options = self._normalize_options(raw_options)

            if not options:
                return {
                    "status": "no_results",
                    "reason": "No flight options found for the given criteria.",
                    "search_params": search_params,
                    "best_option": None,
                    "all_options": [],
                    "count": 0,
                }

            best = select_best_flight(options)

            return {
                "status": "success",
                "reason": None,
                "search_params": search_params,
                "best_option": best,
                "all_options": options,
                "count": len(options),
            }

        except Exception as exc:
            return {
                "status": "error",
                "reason": f"Flight search failed: {exc}",
                "search_params": search_params,
                "best_option": None,
                "all_options": [],
                "count": 0,
            }

    @staticmethod
    def _normalize_destination(value: str | None) -> str:
        destination = str(value or "").strip()
        return destination if destination else "Unknown"

    def _normalize_budget_tier(self, value: str | None) -> str:
        budget = str(value or "").strip().lower()
        return budget if budget in self.ALLOWED_BUDGETS else "medium"

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
    def _normalize_days(value: int | None) -> int | None:
        if value is None:
            return None
        try:
            days = int(value)
            return max(1, min(30, days))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_options(raw_options: Any) -> list[dict[str, Any]]:
        if raw_options is None:
            return []

        if not isinstance(raw_options, list):
            return []

        normalized: list[dict[str, Any]] = []
        for option in raw_options:
            if option is None:
                continue

            if isinstance(option, dict):
                normalized.append(option)
                continue

            if is_dataclass(option):
                normalized.append(asdict(option))
                continue

            if hasattr(option, "__dict__"):
                normalized.append(vars(option))
                continue

        return normalized