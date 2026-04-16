"""Fallback activity search and itinerary generation tools."""

from __future__ import annotations


def search_activities(
    destination: str,
    style: str,
    month: str | None = None,
    travelers: int | None = None,
) -> list[str]:
    """Return deterministic activities for experience planning fallback.

    The activity list is style-aware and lightly adjusted for seasonality
    and group size so the fallback remains useful even without an LLM.
    """
    destination = _normalize_location(destination, fallback="the destination")
    style = _normalize_style(style)
    month = _normalize_optional_text(month)
    travelers = _normalize_positive_int(travelers, default=1)

    base = [
        f"Old Town walking tour in {destination}",
        f"Local food market visit in {destination}",
        f"Sunset viewpoint session in {destination}",
    ]

    style_extras = {
        "adventure": [
            f"Coastal hike near {destination}",
            f"Kayak half-day trip around {destination}",
            f"Outdoor scenic trail exploration in {destination}",
        ],
        "relaxation": [
            f"Spa afternoon in {destination}",
            f"Beach or park chill day in {destination}",
            f"Slow café morning and wellness break in {destination}",
        ],
        "culture": [
            f"Museum pass day in {destination}",
            f"Historic district guided tour in {destination}",
            f"Architecture walk in {destination}",
        ],
        "foodie": [
            f"Street food tasting in {destination}",
            f"Cooking class with a local chef in {destination}",
            f"Evening restaurant crawl in {destination}",
        ],
        "balanced": [
            f"Bike tour around {destination}",
            f"Neighborhood café hopping in {destination}",
            f"Mixed local highlights day in {destination}",
        ],
    }

    seasonal = _seasonal_extras(destination=destination, month=month, style=style)
    group_adjusted = _group_extras(destination=destination, travelers=travelers)

    combined = base + style_extras.get(style, style_extras["balanced"]) + seasonal + group_adjusted

    deduped: list[str] = []
    seen: set[str] = set()
    for item in combined:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def build_itinerary_fallback(
    destination: str,
    activities: list[str],
    days: int,
    style: str,
) -> list[str]:
    """Build a deterministic fallback itinerary from activities."""
    destination = _normalize_location(destination, fallback="the destination")
    days = max(1, min(30, int(days)))
    style = _normalize_style(style)

    if not activities:
        activities = [f"Explore local highlights in {destination}"]

    pacing_note = {
        "adventure": "Keep the day active with time for recovery in the evening.",
        "relaxation": "Maintain a slow pace with flexible downtime.",
        "culture": "Balance landmark visits with unstructured local exploration.",
        "foodie": "Leave room for leisurely meals and neighborhood discoveries.",
        "balanced": "Mix sightseeing, food, and rest across the day.",
    }[style]

    itinerary: list[str] = []
    for day in range(1, days + 1):
        activity = activities[(day - 1) % len(activities)]
        itinerary.append(f"Day {day}: {activity}. {pacing_note}")

    return itinerary


def _seasonal_extras(destination: str, month: str | None, style: str) -> list[str]:
    if not month:
        return []

    normalized = month.strip().lower()

    summer_months = {"june", "july", "august"}
    winter_months = {"december", "january", "february"}
    shoulder_months = {"april", "may", "september", "october"}

    if normalized in summer_months:
        if style == "adventure":
            return [f"Sunrise outdoor excursion near {destination}"]
        if style == "relaxation":
            return [f"Open-air leisure afternoon in {destination}"]
        return [f"Evening outdoor highlights walk in {destination}"]

    if normalized in winter_months:
        if style == "culture":
            return [f"Indoor heritage and gallery day in {destination}"]
        if style == "foodie":
            return [f"Cozy local dining discovery in {destination}"]
        return [f"Indoor local highlights experience in {destination}"]

    if normalized in shoulder_months:
        return [f"Scenic neighborhood exploration in {destination}"]

    return []


def _group_extras(destination: str, travelers: int) -> list[str]:
    if travelers <= 1:
        return [f"Solo-friendly discovery walk in {destination}"]
    if travelers == 2:
        return [f"Couples-friendly evening experience in {destination}"]
    return [f"Small-group shared activity in {destination}"]


def _normalize_style(value: str | None) -> str:
    style = str(value or "").strip().lower()
    if style in {"adventure", "relaxation", "culture", "foodie", "balanced"}:
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