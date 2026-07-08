"""New York City loader for the Tablecloth build pipeline.

The Yelp Open Dataset that powers the rest of Tablecloth has *zero* New York
City coverage (Yelp never released NYC in its open dataset). To give the app
real five-borough coverage we pull NYC restaurants from the UCSD "Google Local"
review corpus (McAuley group, 2021) — a large, static, freely-downloadable
academic dataset with genuine long-form review text, organised by US state.

This module is a *companion* to ``build_dataset.py``: it exposes :func:`load_nyc`,
which returns ``(chosen, reviews)`` DataFrames in exactly the same shape
``build_dataset`` produces for the Yelp slice, so the NYC rows flow through the
identical VADER / aspect / discrepancy / LDA pipeline and land in the same
processed artifacts. No NYC-specific analysis logic lives here — only sourcing,
NYC filtering, and sampling.

Source (see the README "Data sources" section for the exact provenance):
    https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/
    meta-New_York.json.gz        (business metadata, ~61 MB gzipped)
    review-New_York_10.json.gz   (10-core reviews, ~1.3 GB gzipped)

Both raw files are gitignored (``data/raw/``); only the derived output is
committed. Run ``build_dataset.py`` to regenerate everything.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"

META_FILE = "meta-New_York.json.gz"
REVIEW_FILE = "review-New_York_10.json.gz"

# --- NYC sampling parameters (documented in the README) ---------------------
# Mirrors the Yelp slice's density philosophy, tuned for a single dense metro:
# keep only well-reviewed places, cap per borough so Manhattan doesn't dominate,
# then take a few hundred — comparable in scale to the existing per-city corpus.
NYC_MIN_REVIEWS = 100        # density floor within the 10-core review file
NYC_PER_BOROUGH_CAP = 90     # geographic spread across the five boroughs
NYC_TARGET_RESTAURANTS = 350 # final NYC restaurant count (a few hundred)
NYC_REVIEWS_PER_RESTAURANT = 140  # most-recent reviews kept per restaurant
MIN_TEXT_LEN = 40            # same text floor build_dataset applies to Yelp

DATA_SOURCE = "google_local_reviews"

# The five boroughs, as they appear in the Google address string's city field,
# normalised to a canonical borough name used as the app's ``city``.
_BOROUGH_MAP = {
    "new york": "Manhattan",
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "the bronx": "Bronx",
    "staten island": "Staten Island",
}

# Trailing ", <City>, NY <ZIP>" of a Google address string.
_CITY_ZIP = re.compile(r",\s*([A-Za-z .]+),\s*NY\s*(\d{5})")


def _borough_and_zip(address: str) -> Tuple[str | None, str]:
    """Return ``(canonical_borough, postal_code)`` or ``(None, "")``."""
    m = _CITY_ZIP.search(address or "")
    if not m:
        return None, ""
    borough = _BOROUGH_MAP.get(m.group(1).strip().lower())
    return borough, m.group(2)


def _load_nyc_restaurant_meta(meta_path: Path) -> Dict[str, dict]:
    """Restaurant businesses in the five boroughs, keyed by ``gmap_id``."""
    out: Dict[str, dict] = {}
    with gzip.open(meta_path, "rt", encoding="utf-8") as f:
        for line in f:
            b = json.loads(line)
            cats = b.get("category") or []
            if not any("restaurant" in (c or "").lower() for c in cats):
                continue
            borough, postal = _borough_and_zip(b.get("address") or "")
            if borough is None:
                continue
            lat, lon = b.get("latitude"), b.get("longitude")
            if lat is None or lon is None:
                continue
            out[b["gmap_id"]] = {
                "business_id": b["gmap_id"],
                "name": b.get("name") or "",
                "city": borough,
                "state": "NY",
                "postal_code": postal,
                "latitude": float(lat),
                "longitude": float(lon),
                # Match the Yelp comma-joined category string shape.
                "categories": ", ".join(c for c in cats if c),
                "stars": float(b.get("avg_rating") or 0.0),
                "review_count": int(b.get("num_of_reviews") or 0),
            }
    return out


def _count_reviews(review_path: Path, nyc_ids: set) -> Dict[str, int]:
    """Pass 1: count usable (text >= MIN_TEXT_LEN) reviews per NYC restaurant."""
    counts: Dict[str, int] = {}
    with gzip.open(review_path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            gid = r.get("gmap_id")
            if gid not in nyc_ids:
                continue
            text = r.get("text")
            if not text or len(text) < MIN_TEXT_LEN:
                continue
            counts[gid] = counts.get(gid, 0) + 1
    return counts


def _collect_reviews(review_path: Path, keep_ids: set) -> pd.DataFrame:
    """Pass 2: gather all usable reviews for the selected restaurants."""
    rows = []
    with gzip.open(review_path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            gid = r.get("gmap_id")
            if gid not in keep_ids:
                continue
            text = r.get("text")
            if not text or len(text) < MIN_TEXT_LEN:
                continue
            rows.append((
                f"{gid}:{r.get('user_id')}:{r.get('time')}",  # synthetic review_id
                gid,
                r.get("time"),
                float(r.get("rating")),
                text,
            ))
    df = pd.DataFrame(rows, columns=["review_id", "business_id", "time", "stars", "text"])
    df["date"] = pd.to_datetime(df["time"], unit="ms")
    df["useful"] = 0  # Google Local has no "useful" vote analogue
    df["data_source"] = DATA_SOURCE
    return df[["review_id", "business_id", "date", "stars", "text", "useful", "data_source"]]


def _select(meta: Dict[str, dict], counts: Dict[str, int]) -> pd.DataFrame:
    """Pick densely-reviewed restaurants with spread across the five boroughs."""
    rows = [
        {**meta[gid], "sampled_reviews": n}
        for gid, n in counts.items()
        if gid in meta and n >= NYC_MIN_REVIEWS
    ]
    cand = pd.DataFrame(rows)
    if cand.empty:
        return cand
    cand = cand.sort_values("sampled_reviews", ascending=False)
    cand = cand.groupby("city", group_keys=False).head(NYC_PER_BOROUGH_CAP)
    cand = cand.sort_values("sampled_reviews", ascending=False).head(NYC_TARGET_RESTAURANTS)
    cand["data_source"] = DATA_SOURCE
    return cand.reset_index(drop=True)


def load_nyc(raw_dir: Path = RAW) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return ``(chosen, reviews)`` for NYC, shaped like the Yelp slice.

    ``chosen`` columns: business_id, name, city (borough), state, postal_code,
    latitude, longitude, categories, stars, review_count, sampled_reviews,
    data_source. ``reviews`` columns: review_id, business_id, date, stars, text,
    useful, data_source (most-recent NYC_REVIEWS_PER_RESTAURANT per restaurant).

    Returns two empty DataFrames if the raw NYC files are not present, so the
    Yelp-only build still works without them.
    """
    meta_path = raw_dir / META_FILE
    review_path = raw_dir / REVIEW_FILE
    if not meta_path.exists() or not review_path.exists():
        print(f"  [nyc] raw files not found in {raw_dir} - skipping NYC.")
        return pd.DataFrame(), pd.DataFrame()

    print("  [nyc] loading five-borough restaurant metadata ...")
    meta = _load_nyc_restaurant_meta(meta_path)
    print(f"  [nyc] {len(meta):,} NYC restaurant businesses in metadata.")

    print("  [nyc] pass 1/2: counting reviews per restaurant ...")
    counts = _count_reviews(review_path, set(meta))

    chosen = _select(meta, counts)
    if chosen.empty:
        print("  [nyc] no restaurants cleared the density floor - skipping NYC.")
        return pd.DataFrame(), pd.DataFrame()
    print(f"  [nyc] selected {len(chosen)} restaurants across "
          f"{chosen['city'].nunique()} boroughs: "
          f"{dict(chosen['city'].value_counts())}")

    print("  [nyc] pass 2/2: collecting reviews for selected restaurants ...")
    rev = _collect_reviews(review_path, set(chosen["business_id"]))
    # Keep the most-recent N reviews per restaurant (same rule as the Yelp slice).
    rev = (rev.sort_values("date")
              .groupby("business_id", group_keys=False)
              .tail(NYC_REVIEWS_PER_RESTAURANT)
              .reset_index(drop=True))
    # Refresh sampled_reviews to the kept count so aggregates are exact.
    kept = rev.groupby("business_id").size()
    chosen["sampled_reviews"] = chosen["business_id"].map(kept).fillna(0).astype(int)
    chosen = chosen[chosen["sampled_reviews"] > 0].reset_index(drop=True)
    print(f"  [nyc] kept {len(rev):,} reviews across {len(chosen)} restaurants.")
    return chosen, rev


if __name__ == "__main__":
    c, r = load_nyc()
    print(f"\nNYC: {len(c)} restaurants, {len(r):,} reviews")
    if not c.empty:
        print(c[["name", "city", "sampled_reviews", "stars"]].head(10).to_string())
