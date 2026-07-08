"""Tablecloth API - Consumer Review & Sentiment Intelligence for restaurants.

A read-only REST API over a pre-computed sentiment/aspect/topic analysis of a
sample of the Yelp Open Dataset (see ``build_dataset.py`` and the root
README for methodology). Everything here is fast in-memory lookups; no NLP
runs at request time.
"""

from __future__ import annotations

import math
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .data_store import get_store

app = FastAPI(
    title="Tablecloth API",
    description="Consumer review & sentiment intelligence for restaurants, "
                 "built on a sampled slice of the Yelp Open Dataset.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clean(v):
    """Recursively replace NaN/inf with None so JSON encoding never breaks."""
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def _card(r: dict) -> dict:
    """Slim projection of a restaurant record for list/browse views."""
    return {
        "business_id": r["business_id"],
        "name": r["name"],
        "city": r["city"],
        "state": r["state"],
        "categories": r["categories"],
        "yelp_stars": r["yelp_stars"],
        "avg_stars": r["avg_stars"],
        "avg_sentiment": r["avg_sentiment"],
        "pct_positive": r["pct_positive"],
        "pct_negative": r["pct_negative"],
        "sampled_reviews": r["sampled_reviews"],
        "top_topics": r["top_topics"][:2],
        "discrepancy": r["discrepancy"],
    }


@app.get("/api/meta")
def get_meta():
    """Dataset provenance, sampling parameters, and corpus-level stats."""
    return get_store().meta


@app.get("/api/filters")
def get_filters():
    """Distinct cities/states/categories for building UI filter controls."""
    store = get_store()
    return {"cities": store.cities, "states": store.states, "categories": store.categories}


@app.get("/api/topics")
def list_topics():
    """The corpus-wide LDA topic model: labels, top terms, review counts."""
    return get_store().topics


@app.get("/api/restaurants")
def list_restaurants(
    city: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    min_stars: Optional[float] = Query(None, ge=1, le=5),
    min_sentiment: Optional[float] = Query(None, ge=-1, le=1),
    discrepancy: Optional[str] = Query(
        None, description="'positive_text_low_star' | 'negative_text_high_star'"
    ),
    sort: str = Query("sampled_reviews", description="avg_stars|avg_sentiment|sampled_reviews|name"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(60, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Browse / filter restaurants for the card-based explorer."""
    store = get_store()
    rows = store.restaurants

    if city:
        rows = [r for r in rows if r["city"].lower() == city.lower()]
    if state:
        rows = [r for r in rows if r["state"].lower() == state.lower()]
    if category:
        rows = [r for r in rows if any(category.lower() == c.lower() for c in r["categories"])]
    if min_stars is not None:
        rows = [r for r in rows if r["avg_stars"] >= min_stars]
    if min_sentiment is not None:
        rows = [r for r in rows if r["avg_sentiment"] >= min_sentiment]
    if discrepancy:
        key = f"pct_{discrepancy}"
        rows = [r for r in rows if r["discrepancy"].get(key, 0) >= 0.15]

    reverse = order == "desc"
    if sort == "name":
        rows = sorted(rows, key=lambda r: r["name"].lower(), reverse=reverse)
    else:
        rows = sorted(rows, key=lambda r: r.get(sort, 0), reverse=reverse)

    total = len(rows)
    page = rows[offset: offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "results": [_clean(_card(r)) for r in page]}


@app.get("/api/restaurants/{business_id}")
def get_restaurant(business_id: str):
    """Full detail record for a single restaurant: trend, aspects, topics,
    highlight pull-quotes, and star/sentiment discrepancy summary."""
    store = get_store()
    r = store.get(business_id)
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return _clean(r)


@app.get("/api/restaurants/{business_id}/reviews")
def get_restaurant_reviews(
    business_id: str,
    limit: int = Query(30, ge=1, le=140),
    offset: int = Query(0, ge=0),
    flag: Optional[str] = Query(None, description="Filter to a discrepancy_flag value"),
):
    """Paginated review drilldown with per-review sentiment/aspect/discrepancy."""
    store = get_store()
    if not store.get(business_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")

    df = store.reviews_for(business_id)
    if flag:
        df = df[df["discrepancy_flag"] == flag]

    total = len(df)
    page = df.iloc[offset: offset + limit]
    records = page.assign(date=page["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
    return {"total": total, "limit": limit, "offset": offset, "results": [_clean(rec) for rec in records]}


@app.get("/api/compare")
def compare(a: str, b: str):
    """Side-by-side comparison payload for two restaurants."""
    store = get_store()
    ra, rb = store.get(a), store.get(b)
    missing = [bid for bid, r in [(a, ra), (b, rb)] if not r]
    if missing:
        raise HTTPException(status_code=404, detail=f"Restaurant(s) not found: {missing}")
    return {"a": _clean(ra), "b": _clean(rb)}


@app.get("/api/geo")
def geo_aggregate():
    """City-level aggregation: restaurant count, avg sentiment/stars, discrepancy rate."""
    store = get_store()
    by_city: dict = {}
    for r in store.restaurants:
        key = (r["city"], r["state"])
        agg = by_city.setdefault(key, {
            "city": r["city"], "state": r["state"], "restaurants": 0,
            "sentiment_sum": 0.0, "stars_sum": 0.0,
            "lat_sum": 0.0, "lon_sum": 0.0,
        })
        agg["restaurants"] += 1
        agg["sentiment_sum"] += r["avg_sentiment"]
        agg["stars_sum"] += r["avg_stars"]
        agg["lat_sum"] += r["latitude"]
        agg["lon_sum"] += r["longitude"]

    out = []
    for agg in by_city.values():
        n = agg["restaurants"]
        out.append({
            "city": agg["city"],
            "state": agg["state"],
            "restaurants": n,
            "avg_sentiment": round(agg["sentiment_sum"] / n, 4),
            "avg_stars": round(agg["stars_sum"] / n, 3),
            "latitude": round(agg["lat_sum"] / n, 4),
            "longitude": round(agg["lon_sum"] / n, 4),
        })
    out.sort(key=lambda x: x["restaurants"], reverse=True)
    return out


@app.get("/api/trend")
def time_aggregate():
    """Corpus-wide monthly sentiment/rating trend across all sampled reviews."""
    store = get_store()
    df = store.reviews.set_index("date").sort_index()
    monthly = df.resample("MS").agg(
        avg_sentiment=("sentiment", "mean"),
        avg_stars=("stars", "mean"),
        review_count=("stars", "size"),
    ).dropna()
    return [
        {"month": idx.strftime("%Y-%m"),
         "avg_sentiment": round(float(row.avg_sentiment), 4),
         "avg_stars": round(float(row.avg_stars), 3),
         "count": int(row.review_count)}
        for idx, row in monthly.iterrows()
    ]


@app.get("/api/health")
def health():
    store = get_store()
    return {"status": "ok", "restaurants": len(store.restaurants), "reviews": len(store.reviews)}
