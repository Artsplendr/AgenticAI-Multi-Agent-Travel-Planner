# Autonomous Travel Planner (Multi-Agent System with LangGraph)


An intelligent, multi-agent system that plans an end-to-end travel experience using specialized AI agents collaborating through a LangGraph orchestration workflow.  The demo is built with a Streamlit UI.

## Overview
This project demonstrates a collaborative multi-agent architecture where each agent is responsible for a specific aspect of trip planning. The system combines parallel execution, shared state, and iterative refinement to generate optimized travel plans tailored to user preferences.

Built with:
	•	LangGraph → agent orchestration & stateful workflows
	•	LLMs (OpenAI / compatible) → reasoning & generation
	•	Tool integrations → flight, hotel, and activity search (mock or real APIs)

## Architecture
The system follows a parallel + aggregation + refinement loop pattern:

```mermaid
User Input
   ↓
User Intent Agent
   ↓
 ┌───────────────┬───────────────┬───────────────┬────────────────┐
 ↓               ↓               ↓               ↓
Flight Agent   Hotel Agent   Experience Agent   Budget Agent
 └───────────────┴───────────────┴───────────────┴────────────────┘
                         ↓
                  Aggregator Agent
                         ↓
                 Refinement Loop (optional)
                         ↓
                  Final Travel Plan

```

## Implemented Agents

- `UserIntentAgent`
	•	Extracts structured preferences from user input
	•	Identifies:
	•	Destination
	•	Dates
	•	Budget
	•	Travel style (luxury, adventure, minimal, etc.)

- `FlightAgent`
	•	Finds optimal flight options
	•	Can integrate with:
	•	Flight APIs (e.g. Amadeus, Skyscanner)
	•	Mock datasets for offline/demo mode
- `HotelAgent`
	•	Suggests accommodations based on:
	•	Budget
	•	Location preferences
	•	Travel style

- `ExperienceAgent`
	•	Recommends:
	•	Activities
	•	Local experiences
	•	Attractions

- `BudgetOptimizerAgent`
	•	Ensures the trip stays within budget
	•	Adjusts:
	•	Hotel class
	•	Activity selection
	•	Flight options
  
- `AggregatorAgent`
	•	Combines outputs from all agents
	•	Resolves conflicts
	•	Produces a cohesive itinerary

### Agent Design Split

- LLM-based: `UserIntentAgent`, `ExperienceAgent`, `AggregatorAgent`
- Tool-based: `FlightAgent`, `HotelAgent`
- Hybrid (rules + LLM): `BudgetOptimizerAgent`

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Environment

Copy `.env.example` to `.env` and fill values if needed.

```bash
cp .env.example .env
```

## Demo Prompt

`Plan a 5-day trip to Barcelona with a medium budget and a mix of relaxation and adventure.`
