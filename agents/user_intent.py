"""LLM-based user intent extraction agent."""

from __future__ import annotations

import re
from dataclasses import dataclass

from tools.llm_tool import LLMTool, LLMToolError


@dataclass
class UserIntent:
    destination: str
    days: int
    budget_tier: str
    style: str
    origin: str | None = None
    month: str | None = None
    travelers: int | None = None


class UserIntentAgent:
    """Extracts structured travel preferences from free text."""

    ALLOWED_BUDGETS = {"low", "medium", "high"}
    ALLOWED_STYLES = {"adventure", "relaxation", "culture", "foodie", "balanced"}

    _BUDGET_KEYWORDS = {
        "low": {"low", "cheap", "budget", "backpacking", "economy", "affordable"},
        "medium": {"medium", "mid", "moderate", "mid-range"},
        "high": {"high", "luxury", "premium", "upscale"},
    }

    _STYLE_KEYWORDS = {
        "adventure": {"adventure", "hiking", "outdoor", "active"},
        "relaxation": {"relax", "relaxation", "calm", "slow", "peaceful"},
        "culture": {"culture", "museum", "history", "art", "architecture"},
        "foodie": {"food", "foodie", "culinary", "restaurant", "local cuisine"},
    }

    _MONTHS = {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    }

    def __init__(self, llm: LLMTool | None = None) -> None:
        self.llm = llm or LLMTool()

    def run(self, prompt: str) -> UserIntent:
        text = prompt.strip()

        try:
            parsed = self.llm.complete_json(
                system_prompt=(
                    "You are a travel intent parser. "
                    "Extract user preferences from the prompt and return only valid JSON "
                    "with keys: destination (string), days (int), budget_tier "
                    "(low|medium|high), style "
                    "(adventure|relaxation|culture|foodie|balanced), "
                    "origin (string or null), month (string or null), "
                    "travelers (int or null). "
                    "Do not add extra keys. "
                    "If a value is unknown, return null for optional fields."
                ),
                user_prompt=text,
            )

            destination = self._normalize_destination(parsed.get("destination"))
            days = self._normalize_days(parsed.get("days"))
            budget_tier = self._normalize_budget_tier(parsed.get("budget_tier"))
            style = self._normalize_style(parsed.get("style"))
            origin = self._normalize_optional_text(parsed.get("origin"))
            month = self._normalize_month(parsed.get("month"))
            travelers = self._normalize_travelers(parsed.get("travelers"))

        except (LLMToolError, TypeError, ValueError, AttributeError):
            normalized = text.lower()
            destination = self._extract_destination(text)
            days = self._extract_days(normalized)
            budget_tier = self._extract_budget_tier(normalized)
            style = self._extract_style(normalized)
            origin = self._extract_origin(text)
            month = self._extract_month(normalized)
            travelers = self._extract_travelers(normalized)

        return UserIntent(
            destination=destination,
            days=days,
            budget_tier=budget_tier,
            style=style,
            origin=origin,
            month=month,
            travelers=travelers,
        )

    @staticmethod
    def _normalize_destination(value: object) -> str:
        destination = str(value or "").strip()
        return destination if destination else "Unknown"

    @staticmethod
    def _normalize_days(value: object) -> int:
        try:
            return max(2, min(14, int(value)))
        except (TypeError, ValueError):
            return 5

    def _normalize_budget_tier(self, value: object) -> str:
        budget = str(value or "").strip().lower()

        if budget in self.ALLOWED_BUDGETS:
            return budget

        synonyms = {
            "budget": "low",
            "cheap": "low",
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

    def _normalize_style(self, value: object) -> str:
        style = str(value or "").strip().lower()

        if style in self.ALLOWED_STYLES:
            return style

        synonyms = {
            "relaxed": "relaxation",
            "relaxing": "relaxation",
            "cultural": "culture",
            "history": "culture",
            "historical": "culture",
            "art": "culture",
            "food": "foodie",
            "culinary": "foodie",
            "restaurants": "foodie",
        }
        return synonyms.get(style, "balanced")

    @staticmethod
    def _normalize_optional_text(value: object) -> str | None:
        text = str(value or "").strip()
        return text if text else None

    def _normalize_month(self, value: object) -> str | None:
        month = str(value or "").strip().lower()
        if not month:
            return None
        return month.capitalize() if month in self._MONTHS else None

    @staticmethod
    def _normalize_travelers(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            travelers = int(value)
            return travelers if travelers > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_destination(text: str) -> str:
        patterns = [
            r"\bto\s+([A-Z][a-zA-Z\s-]{1,40}?)(?=\s+(with|for|in|on|from)\b|[,.!?]|$)",
            r"\bvisit\s+([A-Z][a-zA-Z\s-]{1,40}?)(?=\s+(with|for|in|on|from)\b|[,.!?]|$)",
            r"\bgoing to\s+([A-Z][a-zA-Z\s-]{1,40}?)(?=\s+(with|for|in|on|from)\b|[,.!?]|$)",
            r"\btrip to\s+([A-Z][a-zA-Z\s-]{1,40}?)(?=\s+(with|for|in|on|from)\b|[,.!?]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip(" .,")

        return "Unknown"

    @staticmethod
    def _extract_days(normalized: str) -> int:
        patterns = [
            r"(\d+)\s*[- ]?\s*days?",
            r"for\s+(\d+)\s+days?",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return max(2, min(14, int(match.group(1))))
        return 5

    def _extract_budget_tier(self, normalized: str) -> str:
        for tier, words in self._BUDGET_KEYWORDS.items():
            for word in words:
                if re.search(rf"\b{re.escape(word)}\b", normalized):
                    return tier
        return "medium"

    def _extract_style(self, normalized: str) -> str:
        for style, words in self._STYLE_KEYWORDS.items():
            for word in words:
                if re.search(rf"\b{re.escape(word)}\b", normalized):
                    return style
        return "balanced"

    @staticmethod
    def _extract_origin(text: str) -> str | None:
        patterns = [
            r"\bfrom\s+([A-Z][a-zA-Z\s-]{1,40}?)(?=\s+(to|for|in|on|with)\b|[,.!?]|$)",
            r"\bleaving from\s+([A-Z][a-zA-Z\s-]{1,40}?)(?=\s+(to|for|in|on|with)\b|[,.!?]|$)",
            r"\bflying from\s+([A-Z][a-zA-Z\s-]{1,40}?)(?=\s+(to|for|in|on|with)\b|[,.!?]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip(" .,")

        return None

    def _extract_month(self, normalized: str) -> str | None:
        for month in self._MONTHS:
            if re.search(rf"\b{re.escape(month)}\b", normalized):
                return month.capitalize()
        return None

    @staticmethod
    def _extract_travelers(normalized: str) -> int | None:
        patterns = [
            r"\bfor\s+(\d+)\s+(people|travelers|travellers|adults|persons)\b",
            r"\b(\d+)\s+(people|travelers|travellers|adults|persons)\b",
            r"\bsolo\b",
            r"\bcouple\b",
        ]

        for pattern in patterns[:2]:
            match = re.search(pattern, normalized)
            if match:
                travelers = int(match.group(1))
                return travelers if travelers > 0 else None

        if re.search(patterns[2], normalized):
            return 1
        if re.search(patterns[3], normalized):
            return 2

        return None