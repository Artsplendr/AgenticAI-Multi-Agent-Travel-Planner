"""Streamlit entrypoint for the autonomous travel planner."""

from __future__ import annotations

import json
from html import escape
from typing import Any

import streamlit as st

from graph.travel_graph import TravelPlannerWorkflow


def _apply_readability_styles() -> None:
    """Increase body text size for easier reading."""
    st.markdown(
        """
        <style>
            .stApp, .stMarkdown p, .stMarkdown li, .stText, .stCaption, .stMetric {
                font-size: 1.08rem;
            }
            .stTextInput label, .stTextArea label {
                font-size: 1.14rem;
            }
            .stTextArea textarea {
                font-size: 1.15rem !important;
                line-height: 1.55 !important;
            }
            .stTextArea textarea::placeholder {
                font-size: 1.05rem !important;
            }
            .stCaption {
                font-size: 1.12rem !important;
            }
            .stMetric [data-testid="stMetricValue"] {
                font-size: 1.55rem;
            }
            .stButton button {
                font-size: 1.02rem;
            }
            .plan-cards-row {
                display: flex;
                gap: 14px;
                overflow-x: auto;
                padding: 6px 2px 14px 2px;
                scrollbar-width: thin;
            }
            .plan-card {
                min-width: 320px;
                max-width: 320px;
                border: 1px solid #d8dce6;
                border-radius: 12px;
                padding: 14px 14px 10px 14px;
                background: #ffffff;
                box-shadow: 0 1px 4px rgba(12, 30, 66, 0.08);
            }
            .plan-card h4 {
                margin: 0 0 10px 0;
                font-size: 1.15rem;
            }
            .plan-card p {
                margin: 0 0 8px 0;
                line-height: 1.45;
            }
            .plan-card ul {
                margin: 0 0 8px 20px;
                padding: 0;
            }
            .plan-card li {
                margin-bottom: 6px;
                line-height: 1.35;
            }
            .card-row {
                margin-bottom: 8px;
            }
            .card-label {
                font-weight: 700;
            }
            .card-muted {
                color: #667085;
            }
            .kpi-value-green {
                color: #15803d;
                font-weight: 700;
            }
            .kpi-value-red {
                color: #b42318;
                font-weight: 700;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_plan(plan: dict[str, Any]) -> None:
    """Render the final travel plan in the Streamlit UI."""
    destination = str(plan.get("destination", "Unknown destination"))
    intent = plan.get("intent", {}) or {}
    budget = plan.get("budget", {}) or {}
    flight = plan.get("flight") or {}
    hotel = plan.get("hotel") or {}
    activities = plan.get("activities") or []
    itinerary = plan.get("itinerary") or []
    trip_summary = str(plan.get("trip_summary", "")).strip()
    missing_components = plan.get("missing_components") or []
    agent_statuses = plan.get("agent_statuses") or {}
    refinement_notes = plan.get("refinement_notes") or []

    requested_budget_tier = str(
        intent.get("requested_budget_tier", intent.get("budget_tier", "—"))
    ).title()
    optimized_budget_tier = str(intent.get("budget_tier", "—")).title()

    st.subheader(f"Travel Plan: {destination}")

    if trip_summary:
        st.info(trip_summary)

    if requested_budget_tier != optimized_budget_tier:
        st.warning(
            f"Requested budget tier: {requested_budget_tier} • "
            f"Optimized working budget tier: {optimized_budget_tier}"
        )

    if missing_components:
        st.warning(
            "Some parts of the plan are incomplete: "
            + ", ".join(str(item) for item in missing_components)
        )

    overview_rows = [
        ("Days", str(intent.get("days", "—"))),
        ("Requested Budget", requested_budget_tier),
        ("Optimized Budget", optimized_budget_tier),
        ("Style", str(intent.get("style", "—")).title()),
    ]
    preferences_rows = [
        ("Destination", str(intent.get("destination", destination))),
        ("Origin", str(intent.get("origin") or "Not specified")),
        ("Month", str(intent.get("month") or "Flexible / not specified")),
        ("Travelers", str(intent.get("travelers") or "Not specified")),
        ("Days", str(intent.get("days", "—"))),
    ]
    flight_rows = [
        ("Airline", str(flight.get("airline", "—"))),
        ("Route", str(flight.get("route", "—"))),
        ("Price", f"${flight.get('price', '—')}"),
        ("Stops", str(flight.get("stops", "—"))),
        ("Cabin", str(flight.get("cabin_class", "—"))),
        ("Departure month", str(flight.get("departure_month") or "—")),
    ]
    hotel_rows = [
        ("Name", str(hotel.get("name", "—"))),
        ("Area", str(hotel.get("area", "—"))),
        ("Nightly rate", f"${hotel.get('nightly_rate', '—')}"),
        ("Nights", str(hotel.get("nights", "—"))),
        ("Total", f"${hotel.get('total', '—')}"),
        ("Style match", "Yes" if hotel.get("style_match") else "No"),
    ]
    requested_travelers = intent.get("travelers")
    if requested_travelers:
        hotel_rows.append(("Requested travelers", str(requested_travelers)))

    room_capacity = hotel.get("traveler_capacity")
    if room_capacity:
        hotel_rows.append(("Room capacity (max)", str(room_capacity)))

    amenities = hotel.get("amenities") or []
    if amenities:
        hotel_rows.append(("Amenities", ", ".join(str(item) for item in amenities)))

    budget_rows = [
        ("Target Budget", _format_currency(budget.get("target"), budget.get("currency"))),
        ("Estimated Total", _format_currency(budget.get("estimated_total"), budget.get("currency"))),
        ("Within Budget", "Yes" if budget.get("is_within_budget") else "No"),
    ]
    cost_breakdown = budget.get("cost_breakdown") or {}
    if cost_breakdown:
        budget_rows.extend(
            [
                ("Flight Cost", _format_currency(cost_breakdown.get("flight"), budget.get("currency"))),
                ("Hotel Cost", _format_currency(cost_breakdown.get("hotel"), budget.get("currency"))),
                (
                    "Activities Cost",
                    _format_currency(cost_breakdown.get("activities"), budget.get("currency")),
                ),
            ]
        )
    notes = [str(note) for note in (budget.get("notes") or [])]
    budget_within_target = bool(budget.get("is_within_budget"))
    budget_value_class = "kpi-value-green" if budget_within_target else "kpi-value-red"

    cards = [
        {
            "title": "Trip Overview",
            "rows": _format_card_rows(overview_rows),
            "list": "",
            "text": trip_summary,
        },
        {
            "title": "Trip Preferences",
            "rows": _format_card_rows(preferences_rows),
            "list": "",
            "text": "",
        },
        {
            "title": "Recommended Flight",
            "rows": _format_card_rows(flight_rows),
            "list": "",
            "text": "",
        },
        {
            "title": "Recommended Hotel",
            "rows": _format_card_rows(hotel_rows),
            "list": "",
            "text": "",
        },
        {
            "title": "Activities",
            "rows": "",
            "list": _format_card_list([str(item) for item in activities], "No activities available."),
            "text": "",
        },
        {
            "title": "Itinerary",
            "rows": "",
            "list": _format_card_list([str(item) for item in itinerary], "No itinerary available."),
            "text": "",
        },
        {
            "title": "Budget Check",
            "rows": _format_card_rows(budget_rows, value_class=budget_value_class),
            "list": _format_card_list(notes, "No extra budget notes."),
            "text": "",
        },
    ]

    card_blocks: list[str] = []
    for card in cards:
        text_content = str(card.get("text", "")).strip()
        if text_content:
            text_html = f"<p>{escape(text_content)}</p>"
        else:
            text_html = '<p class="card-muted">No summary available.</p>' if card["title"] == "Trip Overview" else ""
        card_blocks.append(
            f'<section class="plan-card"><h4>{escape(card["title"])}</h4>{text_html}{card["rows"]}{card["list"]}</section>'
        )
    cards_html = "".join(card_blocks)
    st.markdown(f'<div class="plan-cards-row">{cards_html}</div>', unsafe_allow_html=True)

    if refinement_notes:
        with st.expander("Refinement Notes"):
            for note in refinement_notes:
                st.write(f"- {note}")

    with st.expander("Agent Statuses"):
        st.write(agent_statuses)

    with st.expander("View JSON output"):
        st.code(json.dumps(plan, indent=2), language="json")


def _format_currency(value: Any, currency: Any) -> str:
    """Format numeric values as currency for display."""
    currency_code = str(currency or "USD")
    try:
        amount = int(value)
        return f"{currency_code} {amount}"
    except (TypeError, ValueError):
        return "—"


def _format_card_rows(rows: list[tuple[str, str]], value_class: str = "") -> str:
    """Render key-value rows inside a plan card."""
    value_class_attr = f' class="{escape(value_class)}"' if value_class else ""
    parts = [
        (
            '<p class="card-row"><span class="card-label">'
            f'{escape(label)}:</span> <span{value_class_attr}>{escape(value)}</span></p>'
        )
        for label, value in rows
    ]
    return "".join(parts)


def _format_card_list(items: list[str], empty_message: str) -> str:
    """Render list content inside a card."""
    if not items:
        return f'<p class="card-muted">{escape(empty_message)}</p>'
    list_items = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<ul>{list_items}</ul>"


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(
        page_title="Autonomous Travel Planner",
        page_icon="✈️",
        layout="wide",
    )
    _apply_readability_styles()

    st.title("Autonomous Travel Planner")
    st.caption("Multi-agent travel planner demo powered by LangGraph")

    default_prompt = (
        "Plan a 5-day trip to Barcelona from Berlin in June for 2 people "
        "with a medium budget and a mix of relaxation and adventure."
    )
    prompt = st.text_area(
        "Describe your trip request",
        value=default_prompt,
        height=140,
        placeholder=(
            "Example: Plan a 7-day foodie trip to Rome in September "
            "for 2 people with a medium budget."
        ),
    )

    if "latest_plan" not in st.session_state:
        st.session_state["latest_plan"] = None

    if "latest_error" not in st.session_state:
        st.session_state["latest_error"] = None

    if st.button("Generate Plan", type="primary"):
        st.session_state["latest_error"] = None

        if not prompt.strip():
            st.session_state["latest_error"] = "Please enter a trip request."
        else:
            try:
                workflow = TravelPlannerWorkflow()
                plan = workflow.run(prompt.strip())
                st.session_state["latest_plan"] = plan
            except Exception as exc:
                st.session_state["latest_error"] = f"Failed to generate plan: {exc}"

    latest_error = st.session_state.get("latest_error")
    latest_plan = st.session_state.get("latest_plan")

    if latest_error:
        st.error(latest_error)

    if latest_plan:
        render_plan(latest_plan)


if __name__ == "__main__":
    main()