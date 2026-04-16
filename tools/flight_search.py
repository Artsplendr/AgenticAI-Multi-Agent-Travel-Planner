"""Tooling layer for flight search and ranking."""

from __future__ import annotations

from typing import Any


def search_flights(
    destination: str,
    budget_tier: str,
    origin: str | None = None,
    month: str | None = None,
    travelers: int | None = None,
    days: int | None = None,
) -> list[dict[str, Any]]:
    """Mock flight search tool that simulates external API results.

    The tool returns deterministic mock options based on user constraints.
    It is designed for demos, local development, and LangGraph orchestration
    before integrating a real travel API.
    """
    destination = _normalize_location(destination, fallback="Unknown")
    origin = _normalize_location(origin, fallback="Home")
    budget_tier = _normalize_budget_tier(budget_tier)
    month = _normalize_optional_text(month)
    travelers = _normalize_positive_int(travelers, default=1)
    days = _normalize_positive_int(days, default=5)

    if destination == "Unknown":
        return []

    base_by_tier = {
        "low": 280,
        "medium": 430,
        "high": 760,
    }
    base_price = base_by_tier[budget_tier]

    month_multiplier = _month_price_multiplier(month)
    duration_fee = max(0, (days - 5) * 8)
    traveler_fee = max(0, travelers - 1) * 35

    adjusted_base = int(base_price * month_multiplier) + duration_fee + traveler_fee

    options = [
        {
            "airline": "SkyWays",
            "route": f"{origin} -> {destination}",
            "price": adjusted_base,
            "stops": 1,
            "cabin_class": _cabin_class_for_budget(budget_tier),
            "departure_month": month,
            "travelers": travelers,
            "trip_length_days": days,
        },
        {
            "airline": "BlueJet",
            "route": f"{origin} -> {destination}",
            "price": adjusted_base + 85,
            "stops": 0,
            "cabin_class": _cabin_class_for_budget(budget_tier),
            "departure_month": month,
            "travelers": travelers,
            "trip_length_days": days,
        },
        {
            "airline": "CloudAir",
            "route": f"{origin} -> {destination}",
            "price": max(180, adjusted_base - 55),
            "stops": 2,
            "cabin_class": _cabin_class_for_budget(budget_tier),
            "departure_month": month,
            "travelers": travelers,
            "trip_length_days": days,
        },
        {
            "airline": "AeroNova",
            "route": f"{origin} -> {destination}",
            "price": adjusted_base + 40,
            "stops": 1,
            "cabin_class": _cabin_class_for_budget(budget_tier),
            "departure_month": month,
            "travelers": travelers,
            "trip_length_days": days,
        },
    ]

    return sorted(options, key=lambda item: (item["price"], item["stops"], item["airline"]))


def select_best_flight(options: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select the best flight option using a simple weighted ranking.

    Ranking preference:
    1. Lower price
    2. Fewer stops
    3. Stable alphabetical tie-breaker by airline
    """
    if not options:
        return None

    valid_options = [
        option
        for option in options
        if isinstance(option, dict)
        and isinstance(option.get("price"), (int, float))
        and isinstance(option.get("stops"), int)
    ]

    if not valid_options:
        return None

    return sorted(
        valid_options,
        key=lambda item: (item["price"], item["stops"], str(item.get("airline", ""))),
    )[0]


def _normalize_budget_tier(value: str | None) -> str:
    budget = str(value or "").strip().lower()
    if budget in {"low", "medium", "high"}:
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


def _normalize_location(value: str | None, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalize_optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def _normalize_positive_int(value: int | None, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _month_price_multiplier(month: str | None) -> float:
    if not month:
        return 1.0

    normalized = month.strip().lower()

    peak_months = {"june", "july", "august", "december"}
    shoulder_months = {"april", "may", "september", "october"}

    if normalized in peak_months:
        return 1.18
    if normalized in shoulder_months:
        return 1.08
    return 0.96


def _cabin_class_for_budget(budget_tier: str) -> str:
    mapping = {
        "low": "economy",
        "medium": "economy",
        "high": "premium economy",
    }
    return mapping.get(budget_tier, "economy")