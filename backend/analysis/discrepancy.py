"""Star-rating vs. computed-sentiment discrepancy detection.

Consumers do not always rate consistently with the language they write. We map a
1-5 star rating onto the same ``[-1, 1]`` scale as the VADER compound score and
measure the gap. Large gaps are analytically interesting:

* ``positive_text_low_star`` - the reviewer wrote warmly but scored low
  (nuanced criticism, a single dealbreaker, or rating-scale deflation).
* ``negative_text_high_star`` - a glowing star rating with critical language
  (habitual 5-star raters, sarcasm, or "great but...").

Both the per-review gap and the restaurant-level aggregate are exposed so the
UI can surface where headline star ratings hide the real consumer story.
"""

from __future__ import annotations

from typing import Optional

# A review must diverge by at least this much (on the [-1,1] scale) to flag.
DISCREPANCY_THRESHOLD = 0.6


def star_to_scale(stars: float) -> float:
    """Map a 1-5 star rating linearly onto ``[-1, 1]`` (3 stars -> 0)."""
    return (float(stars) - 3.0) / 2.0


def discrepancy(stars: float, compound: float) -> float:
    """Signed gap: ``sentiment - star``.

    Positive => text is warmer than the star rating implies.
    Negative => text is harsher than the star rating implies.
    """
    return round(compound - star_to_scale(stars), 4)


def flag(stars: float, compound: float) -> Optional[str]:
    """Return a discrepancy category, or ``None`` when rating and text agree."""
    gap = discrepancy(stars, compound)
    if gap >= DISCREPANCY_THRESHOLD:
        return "positive_text_low_star"
    if gap <= -DISCREPANCY_THRESHOLD:
        return "negative_text_high_star"
    return None
