"""Token estimation using tiktoken."""

from __future__ import annotations

import tiktoken

_COST_PER_1K: dict[str, tuple[float, float]] = {
    # (prompt, completion) per 1K tokens
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-5-mini": (0.00015, 0.0006),  # placeholder — update when official pricing is available
}


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def estimate_cost(
    prompt_tokens: int, completion_tokens: int, model: str = "gpt-4o"
) -> float:
    costs = _COST_PER_1K.get(model, (0.0025, 0.01))
    return (prompt_tokens / 1000 * costs[0]) + (completion_tokens / 1000 * costs[1])
