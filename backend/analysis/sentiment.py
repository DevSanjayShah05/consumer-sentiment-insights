"""Review-level sentiment scoring.

Uses VADER (Valence Aware Dictionary and sEntiment Reasoner), a lexicon and
rule-based sentiment model tuned for social/short-form English. VADER is chosen
deliberately: it is fast, deterministic, requires no GPU, and produces a
bounded ``compound`` score in ``[-1, 1]`` that is convenient for aggregation and
for comparing against a normalised star rating.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Thresholds recommended by the VADER authors for labelling compound scores.
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    """Return a process-wide singleton analyzer (lexicon load is not free)."""
    return SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    """Return the VADER compound sentiment for ``text`` in ``[-1, 1]``."""
    if not text or not text.strip():
        return 0.0
    return _analyzer().polarity_scores(text)["compound"]


def label_for_score(compound: float) -> str:
    """Map a compound score to a coarse positive/neutral/negative label."""
    if compound >= POSITIVE_THRESHOLD:
        return "positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def score_detail(text: str) -> Dict[str, float]:
    """Return the full VADER breakdown (neg/neu/pos/compound) for ``text``."""
    if not text or not text.strip():
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    return _analyzer().polarity_scores(text)
