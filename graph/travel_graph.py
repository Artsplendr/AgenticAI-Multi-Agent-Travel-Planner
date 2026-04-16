"""LangGraph StateGraph orchestration for the autonomous travel planner."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.aggregator import AggregatorAgent
from agents.budget_agent import BudgetOptimizerAgent
from agents.experience_agent import ExperienceAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.user_intent import UserIntentAgent
from memory.state import TravelPlannerState


class TravelPlannerWorkflow:
    """Coordinates all agents via an explicit LangGraph StateGraph."""

    MAX_REFINEMENTS = 1

    def __init__(self) -> None:
        self.intent_agent = UserIntentAgent()
        self.flight_agent = FlightAgent()
        self.hotel_agent = HotelAgent()
        self.experience_agent = ExperienceAgent()
        self.budget_agent = BudgetOptimizerAgent()
        self.aggregator_agent = AggregatorAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(TravelPlannerState)

        graph.add_node("user_intent", self._node_user_intent)
        graph.add_node("flight", self._node_flight)
        graph.add_node("hotel", self._node_hotel)
        graph.add_node("experience", self._node_experience)
        graph.add_node("budget_optimizer", self._node_budget)
        graph.add_node("refine_plan", self._node_refine_plan)
        graph.add_node("aggregator", self._node_aggregator)

        graph.add_edge(START, "user_intent")
        graph.add_edge("user_intent", "flight")
        graph.add_edge("user_intent", "hotel")
        graph.add_edge("user_intent", "experience")
        graph.add_edge(["flight", "hotel", "experience"], "budget_optimizer")

        graph.add_conditional_edges(
            "budget_optimizer",
            self._route_after_budget,
            {
                "refine_plan": "refine_plan",
                "aggregator": "aggregator",
            },
        )

        graph.add_edge("refine_plan", "flight")
        graph.add_edge("refine_plan", "hotel")
        graph.add_edge("refine_plan", "experience")
        graph.add_edge("aggregator", END)

        return graph.compile()

    def _node_user_intent(self, state: TravelPlannerState) -> dict[str, Any]:
        intent = self.intent_agent.run(state["user_prompt"])

        return {
            "destination": intent.destination,
            "days": intent.days,
            "budget_tier": intent.budget_tier,
            "requested_budget_tier": intent.budget_tier,
            "style": intent.style,
            "origin": intent.origin,
            "month": intent.month,
            "travelers": intent.travelers,
            "intent_data": {
                "destination": intent.destination,
                "days": intent.days,
                "budget_tier": intent.budget_tier,
                "requested_budget_tier": intent.budget_tier,
                "style": intent.style,
                "origin": intent.origin,
                "month": intent.month,
                "travelers": intent.travelers,
            },
            "refinement_count": state.get("refinement_count", 0),
            "refinement_notes": state.get("refinement_notes", []),
        }

    def _node_flight(self, state: TravelPlannerState) -> dict[str, Any]:
        return {
            "flight_data": self.flight_agent.run(
                destination=state.get("destination", "Unknown"),
                budget_tier=state.get("budget_tier", "medium"),
                origin=state.get("origin"),
                month=state.get("month"),
                travelers=state.get("travelers"),
                days=state.get("days"),
            )
        }

    def _node_hotel(self, state: TravelPlannerState) -> dict[str, Any]:
        return {
            "hotel_data": self.hotel_agent.run(
                destination=state.get("destination", "Unknown"),
                days=state.get("days", 5),
                budget_tier=state.get("budget_tier", "medium"),
                style=state.get("style", "balanced"),
                travelers=state.get("travelers"),
                month=state.get("month"),
            )
        }

    def _node_experience(self, state: TravelPlannerState) -> dict[str, Any]:
        return {
            "experience_data": self.experience_agent.run(
                destination=state.get("destination", "Unknown"),
                days=state.get("days", 5),
                style=state.get("style", "balanced"),
                month=state.get("month"),
                travelers=state.get("travelers"),
            )
        }

    def _node_budget(self, state: TravelPlannerState) -> dict[str, Any]:
        flight_data = state.get("flight_data") or {}
        hotel_data = state.get("hotel_data") or {}
        experience_data = state.get("experience_data") or {}

        best_flight = flight_data.get("best_option") or {}
        selected_hotel = hotel_data.get("hotel") or {}
        activities = experience_data.get("activities") or []

        flight_price = self._safe_int(best_flight.get("price"))
        hotel_total = self._safe_int(selected_hotel.get("total"))
        activity_count = len(activities)

        budget_data = self.budget_agent.run(
            budget_tier=state.get("budget_tier", "medium"),
            days=state.get("days", 5),
            flight_price=flight_price,
            hotel_total=hotel_total,
            activity_count=activity_count,
            destination=state.get("destination", "Unknown"),
            style=state.get("style", "balanced"),
            travelers=state.get("travelers"),
        )

        return {
            "budget_data": budget_data,
            "needs_refinement": not bool(budget_data.get("is_within_budget", True)),
        }

    def _node_refine_plan(self, state: TravelPlannerState) -> dict[str, Any]:
        refinement_count = state.get("refinement_count", 0) + 1
        current_budget_tier = str(state.get("budget_tier", "medium")).lower()
        requested_budget_tier = str(
            state.get("requested_budget_tier", current_budget_tier)
        ).lower()

        refined_budget_tier = current_budget_tier
        if current_budget_tier == "high":
            refined_budget_tier = "medium"
        elif current_budget_tier == "medium":
            refined_budget_tier = "low"

        refinement_notes = list(state.get("refinement_notes", []))
        refinement_notes.append(
            f"Refinement round {refinement_count}: kept requested budget as "
            f"'{requested_budget_tier}' but used a lower working tier "
            f"'{refined_budget_tier}' to improve affordability."
        )

        intent_data = dict(state.get("intent_data", {}))
        intent_data["budget_tier"] = refined_budget_tier
        intent_data["requested_budget_tier"] = requested_budget_tier

        return {
            "budget_tier": refined_budget_tier,
            "requested_budget_tier": requested_budget_tier,
            "refinement_count": refinement_count,
            "refinement_notes": refinement_notes,
            "intent_data": intent_data,
        }

    def _node_aggregator(self, state: TravelPlannerState) -> dict[str, Any]:
        intent_data = dict(state.get("intent_data", {}))
        intent_data["budget_tier"] = state.get("budget_tier", intent_data.get("budget_tier"))
        intent_data["requested_budget_tier"] = state.get(
            "requested_budget_tier",
            intent_data.get("requested_budget_tier", state.get("budget_tier")),
        )
        intent_data["destination"] = state.get("destination", intent_data.get("destination"))
        intent_data["origin"] = state.get("origin", intent_data.get("origin"))
        intent_data["month"] = state.get("month", intent_data.get("month"))
        intent_data["travelers"] = state.get("travelers", intent_data.get("travelers"))
        intent_data["days"] = state.get("days", intent_data.get("days"))
        intent_data["style"] = state.get("style", intent_data.get("style"))

        plan = self.aggregator_agent.run(
            destination=state.get("destination", "Unknown"),
            original_prompt=state.get("user_prompt", ""),
            intent=intent_data,
            flight_data=state.get("flight_data", {}),
            hotel_data=state.get("hotel_data", {}),
            experience_data=state.get("experience_data", {}),
            budget_data=state.get("budget_data", {}),
        )

        plan["refinement_notes"] = state.get("refinement_notes", [])

        return {"final_plan": plan}

    def _route_after_budget(self, state: TravelPlannerState) -> str:
        needs_refinement = bool(state.get("needs_refinement", False))
        refinement_count = int(state.get("refinement_count", 0))

        if needs_refinement and refinement_count < self.MAX_REFINEMENTS:
            return "refine_plan"
        return "aggregator"

    def run(self, user_prompt: str) -> dict[str, Any]:
        result = self.graph.invoke(
            {
                "user_prompt": user_prompt,
                "refinement_count": 0,
                "refinement_notes": [],
            }
        )
        return result["final_plan"]

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0