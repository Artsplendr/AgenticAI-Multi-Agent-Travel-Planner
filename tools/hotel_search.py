"""Tooling layer for hotel search and style-aware ranking."""

from __future__ import annotations

from typing import Any


def search_hotels(
    destination: str,
    budget_tier: str,
    travelers: int | None = None,
    month: str | None = None,
) -> list[dict[str, Any]]:
    """Mock hotel search tool that simulates external hotel API results.

    Returns deterministic options based on destination, budget tier, season,
    and traveler count. Designed for demos and local development before
    integrating a real hotel provider API.
    """
    destination = _normalize_location(destination, fallback="Unknown")
    budget_tier = _normalize_budget_tier(budget_tier)
    travelers = _normalize_positive_int(travelers, default=1)
    month = _normalize_optional_text(month)

    if destination == "Unknown":
        return []

    nightly_by_tier = {
        "low": 55,
        "medium": 110,
        "high": 240,
    }
    base_rate = nightly_by_tier[budget_tier]

    month_multiplier = _month_price_multiplier(month)
    traveler_fee = max(0, travelers - 1) * 12

    adjusted_base = int(base_rate * month_multiplier) + traveler_fee

    options = [
        {
            "name": f"City Central Hotel {destination}",
            "nightly_rate": adjusted_base,
            "area": "center",
            "amenities": ["wifi", "breakfast", "walkable location"],
            "traveler_capacity": 2,
        },
        {
            "name": f"Serenity Stay {destination}",
            "nightly_rate": adjusted_base + 30,
            "area": "quiet",
            "amenities": ["spa access", "wifi", "garden lounge"],
            "traveler_capacity": 2,
        },
        {
            "name": f"Trailbase Lodge {destination}",
            "nightly_rate": max(45, adjusted_base - 15),
            "area": "outdoors",
            "amenities": ["trail access", "breakfast", "parking"],
            "traveler_capacity": 3,
        },
        {
            "name": f"Grand Horizon {destination}",
            "nightly_rate": adjusted_base + 65,
            "area": "center",
            "amenities": ["pool", "gym", "concierge"],
            "traveler_capacity": 4,
        },
    ]

    return [
        option
        for option in options
        if option["traveler_capacity"] >= travelers
    ]


def filter_hotels_by_style(
    options: list[dict[str, Any]],
    style: str,
) -> list[dict[str, Any]]:
    """Sort hotel options by style fit, then affordability.

    Preferred areas by style:
    - adventure -> outdoors
    - relaxation -> quiet
    - culture -> center
    - foodie -> center
    - balanced -> center
    """
    if not options:
        return []

    style_area = {
        "adventure": "outdoors",
        "relaxation": "quiet",
        "culture": "center",
        "foodie": "center",
        "balanced": "center",
    }.get(str(style or "").strip().lower(), "center")

    ranked: list[dict[str, Any]] = []

    for option in options:
        if not isinstance(option, dict):
            continue

        normalized = {
            "name": option.get("name", "Unknown Hotel"),
            "nightly_rate": int(option.get("nightly_rate", 0)),
            "area": option.get("area", "unknown"),
            "amenities": option.get("amenities", []),
            "traveler_capacity": option.get("traveler_capacity"),
            "style_match": option.get("area") == style_area,
        }
        ranked.append(normalized)

    return sorted(
        ranked,
        key=lambda item: (
            item["area"] != style_area,
            item["nightly_rate"],
            item["name"],
        ),
    )


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
        return 1.20
    if normalized in shoulder_months:
        return 1.08
    return 0.95