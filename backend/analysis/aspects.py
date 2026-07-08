"""Aspect-based sentiment via keyword-anchored sentence extraction.

We track four consumer-relevant aspects of a restaurant experience: ``food``,
``service``, ``price`` and ``ambiance``. For each aspect we maintain a curated
lexicon of anchor terms. A review is split into sentences; every sentence that
mentions an aspect's anchor terms contributes its VADER sentiment to that
aspect. The aspect score is the mean sentiment across matching sentences, so a
review can express, say, positive sentiment about food while being negative
about price.

This keyword-anchored approach is transparent and cheap (no training data or
model required) which suits an interpretable consumer-insights tool.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .sentiment import score_text

ASPECTS: Dict[str, List[str]] = {
    "food": [
        "food", "dish", "meal", "menu", "flavor", "flavour", "taste", "tasty",
        "delicious", "portion", "cooked", "fresh", "appetizer", "entree",
        "dessert", "sauce", "spicy", "bland", "seasoned", "quality", "plate",
        "chef", "ingredient", "cuisine",
    ],
    "service": [
        "service", "staff", "server", "waiter", "waitress", "waitstaff",
        "host", "hostess", "manager", "attentive", "rude", "friendly",
        "wait", "waited", "slow", "quick", "prompt", "greeted", "bartender",
        "hospitality", "accommodating",
    ],
    "price": [
        "price", "priced", "pricing", "expensive", "cheap", "overpriced",
        "value", "affordable", "cost", "worth", "bill", "money", "dollar",
        "budget", "deal", "reasonable", "pricey",
    ],
    "ambiance": [
        "ambiance", "ambience", "atmosphere", "decor", "vibe", "music",
        "cozy", "romantic", "noisy", "loud", "clean", "dirty", "seating",
        "patio", "lighting", "interior", "crowded", "spacious", "comfortable",
        "setting",
    ],
}

# Pre-compile a word-boundary regex per aspect for fast matching.
_ASPECT_PATTERNS = {
    aspect: re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    for aspect, words in ASPECTS.items()
}

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> List[str]:
    """Lightweight sentence splitter (no heavyweight NLP dependency)."""
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if s.strip()]


def aspect_sentiment(text: str) -> Dict[str, Optional[dict]]:
    """Compute per-aspect sentiment for a single review.

    Returns a mapping ``aspect -> {"score": float, "mentions": int}`` or
    ``None`` for aspects the review never mentions.
    """
    sentences = split_sentences(text)
    buckets: Dict[str, List[float]] = {a: [] for a in ASPECTS}

    for sentence in sentences:
        for aspect, pattern in _ASPECT_PATTERNS.items():
            if pattern.search(sentence):
                buckets[aspect].append(score_text(sentence))

    result: Dict[str, Optional[dict]] = {}
    for aspect, scores in buckets.items():
        if scores:
            result[aspect] = {
                "score": round(sum(scores) / len(scores), 4),
                "mentions": len(scores),
            }
        else:
            result[aspect] = None
    return result
