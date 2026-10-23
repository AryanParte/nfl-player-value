"""Observed preplay context; no pressure, time-to-throw or postplay adjustments."""

from math import isfinite


CONTEXT = ("down", "ydstogo", "yardline_100", "game_seconds_remaining", "qtr", "score_differential")


def parse_context(row: dict) -> dict:
    context = {name: float(row[name]) for name in CONTEXT}
    if not all(isfinite(x) for x in context.values()):
        raise ValueError("nonfinite context")
    if context["down"] not in {1, 2, 3, 4} or context["qtr"] not in {1, 2, 3, 4, 5}:
        raise ValueError("invalid down or quarter")
    if not (0 <= context["ydstogo"] <= 100 and 0 <= context["yardline_100"] <= 100 and 0 <= context["game_seconds_remaining"] <= 3600):
        raise ValueError("invalid distance, field position or time")
    return context
