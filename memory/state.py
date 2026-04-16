"""Shared LangGraph state for the autonomous travel planner."""

from __future__ import annotations

from typing import Any, TypedDict


class TravelPlannerState(TypedDict, total=False):
    """State shared across the LangGraph travel planning workflow."""

    # Original user input
    user_prompt: str

    # Parsed intent fields
    destination: str
    days: int
    budget_tier: str
    requested_budget_tier: str
    style: str
    origin: str | None
    month: str | None
    travelers: int | None

    # Structured intent payload for downstream use
    intent_data: dict[str, Any]

    # Agent outputs
    flight_data: dict[str, Any]
    hotel_data: dict[str, Any]
    experience_data: dict[str, Any]
    budget_data: dict[str, Any]

    # Workflow control
    needs_refinement: bool
    refinement_count: int
    refinement_notes: list[str]

    # Final output
    final_plan: dict[str, Any]