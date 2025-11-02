import os
import re
import json
import logging
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


def _rule_based_motivation(user_input: str) -> List[str]:
    text = user_input.lower()
    suggestions: List[str] = []

    # Exam/test-specific motivation
    if any(w in text for w in ["exam", "test", "quiz", "midterm", "final"]):
        suggestions.append("You've prepared for this! Trust your knowledge and take it one question at a time. 📚")
        suggestions.append("Take deep breaths before starting. A calm mind recalls information better than a stressed one. 🧘")
        suggestions.append("Remember: You don't need perfection, just progress. Answer what you know first, then tackle the rest. ✨")
    # Simple heuristics
    elif any(w in text for w in ["tired", "exhausted", "burnout"]):
        suggestions.append("You're allowed to rest — take a short, intentional break and come back with fresh energy.")
        suggestions.append("Break your work into 15-minute sprints; small wins will rebuild momentum.")
        suggestions.append("Celebrate one tiny thing you did well today, however small.")
    elif any(w in text for w in ["stuck", "blocked", "can't", "cannot", "unable"]):
        suggestions.append("Try one small experiment — a tiny step reduces decision friction and often reveals the way forward.")
        suggestions.append("Ask a colleague or write down the exact constraint; naming it often clarifies a solution.")
        suggestions.append("If it's big, split it into 'next actions' you can complete in under 30 minutes.")
    elif any(w in text for w in ["sad", "down", "depressed", "unhappy"]):
        suggestions.append("You matter. Name one thing that made you smile recently and keep it close.")
        suggestions.append("Do a 5-minute grounding exercise: breathe deeply and list 3 facts around you.")
        suggestions.append("If this persists, consider reaching out to someone you trust or a professional.")
    else:
        # Generic motivational template
        suggestions.append("You're closer than you think — focus on the next small step and start there.")
        suggestions.append("Set a 25-minute timer and do one thing; momentum builds quickly from action.")
        suggestions.append("Remember progress beats perfection: aim for progress today, no matter how small.")

    return suggestions


async def _call_remote_model(user_input: str) -> List[str]:
    # Try to call an OpenAI-compatible chat completions endpoint if configured.
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key or not base_url:
        raise RuntimeError("OPENAI_API_KEY or OPENAI_BASE_URL not configured")

    # Normalize base URL
    base_url = base_url.rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": os.getenv("A2A_MODEL", "gpt-3.5-turbo"),
        "messages": [
            {"role": "system", "content": "You are a concise, empathetic motivational coach. Return output as a numbered list or JSON array of short strings."},
            {"role": "user", "content": f"User input: {user_input}\n\nPlease provide exactly 3 short motivational suggestions (1-2 sentences each). Return only a JSON array of strings if possible."},
        ],
        "max_tokens": 200,
        "temperature": 0.8,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Try to extract content following OpenAI chat response schema
    content = None
    if isinstance(data, dict):
        choices = data.get("choices")
        if choices and len(choices) > 0:
            message = choices[0].get("message") or {}
            content = message.get("content") or choices[0].get("text")

    if not content:
        # Fallback: try to find text fields
        if isinstance(data, dict):
            content = json.dumps(data)

    # Attempt to parse JSON array from model output
    suggestions: List[str] = []
    if content:
        # Try to extract a JSON array
        try:
            # Find first '[' and last ']' to try to decode
            m = re.search(r"\[.*\]", content, re.DOTALL)
            if m:
                arr_text = m.group(0)
                arr = json.loads(arr_text)
                if isinstance(arr, list):
                    suggestions = [str(x).strip() for x in arr][:3]
            if not suggestions:
                # Fallback: split into lines and clean numbers/bullets
                lines = [re.sub(r"^\s*\d+[\).:-]?\s*", "", ln).strip() for ln in content.splitlines() if ln.strip()]
                if lines:
                    suggestions = [ln for ln in lines][:3]
        except Exception:
            logger.exception("Failed parsing model output; falling back to lines")

    if not suggestions:
        raise RuntimeError("Model returned no usable suggestions")

    return suggestions


async def generate_motivation(user_input: str) -> Dict[str, Any]:
    """Return a dict with motivations and metadata.

    If OPENAI_API_KEY and OPENAI_BASE_URL are configured, attempt a remote call; otherwise, return rule-based suggestions.
    """
    # Validate input
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("user_input must be a non-empty string")

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if api_key and base_url:
            try:
                suggestions = await _call_remote_model(user_input)
                return {"motivations": suggestions, "source": "remote_model"}
            except Exception:
                logger.exception("Remote model call failed; falling back to local rules")

        # Local fallback
        suggestions = _rule_based_motivation(user_input)
        return {"motivations": suggestions, "source": "local"}

    except Exception as e:
        logger.exception("generate_motivation error")
        raise
