from __future__ import annotations

import json
from typing import Any

from .config import Desire


def extract_json_object(text: str) -> dict[str, Any]:
    body = (text or "").strip()
    if not body:
        raise ValueError("Model returned empty content.")
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start_positions = [idx for idx, ch in enumerate(body) if ch == "{"]
    for start in start_positions:
        depth = 0
        for idx in range(start, len(body)):
            ch = body[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = body[start : idx + 1]
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, dict):
                        return parsed
                    break
    raise ValueError("Could not extract a JSON object from model output.")


def _unwrap_scores_container(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    if isinstance(payload.get("scores"), list):
        return payload["scores"]

    for key in ("result", "results", "response", "output", "data", "json", "answer"):
        nested = payload.get(key)
        if isinstance(nested, dict) and isinstance(nested.get("scores"), list):
            return nested["scores"]
        if isinstance(nested, list) and all(isinstance(item, dict) for item in nested):
            if all("id" in item and "score" in item for item in nested):
                return nested

    if all(isinstance(value, dict) for value in payload.values()):
        for nested in payload.values():
            if isinstance(nested.get("scores"), list):
                return nested["scores"]
    return None


def normalize_scores(payload: dict[str, Any], desires: tuple[Desire, ...]) -> list[dict[str, Any]]:
    expected = {desire.id: desire for desire in desires}
    raw_scores = _unwrap_scores_container(payload)
    if not isinstance(raw_scores, list):
        raise ValueError("Payload is missing a top-level 'scores' list.")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_scores:
        if not isinstance(item, dict):
            raise ValueError("Each score row must be an object.")
        desire_id = str(item.get("id") or "").strip()
        if desire_id not in expected:
            raise ValueError(f"Unexpected desire id: {desire_id or '<empty>'}")
        if desire_id in seen:
            raise ValueError(f"Duplicate desire id: {desire_id}")
        seen.add(desire_id)

        score = item.get("score")
        try:
            score_int = int(score)
        except (TypeError, ValueError):
            raise ValueError(f"Non-integer score for {desire_id}: {score!r}") from None
        if score_int < 1 or score_int > 100:
            raise ValueError(f"Score for {desire_id} is out of range: {score_int}")

        explanation = str(item.get("explanation") or "").strip()
        if not explanation:
            raise ValueError(f"Missing explanation for {desire_id}")

        normalized.append(
            {
                "id": desire_id,
                "label": expected[desire_id].label,
                "score": score_int,
                "explanation": explanation,
            }
        )

    missing = [desire.id for desire in desires if desire.id not in seen]
    if missing:
        raise ValueError(f"Missing desire ids: {', '.join(missing)}")

    return sorted(normalized, key=lambda item: item["id"])
