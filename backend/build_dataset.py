"""Offline build pipeline for Tablecloth.

Reads the raw Yelp Open Dataset (restaurant slice), runs every expensive NLP
step exactly once, and writes small derived artifacts that the FastAPI service
loads at startup. Running this is optional for reviewers - the derived
artifacts are committed to the repo. Re-run it only to regenerate them:

    python build_dataset.py

Pipeline: select densely-reviewed restaurants with geographic spread -> cap and
clean reviews -> VADER review sentiment -> keyword-anchored aspect sentiment ->
star/sentiment discrepancy -> corpus LDA topics -> per-restaurant aggregates ->
JSON/Parquet artifacts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from analysis import aspects, discrepancy, sentiment, topics
from build_nyc_dataset import load_nyc

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
OUT = HERE / "data" / "processed"

# --- Sampling parameters (documented in the README) -------------------------
MIN_REVIEWS_PER_RESTAURANT = 100   # density floor within the downloaded shards
PER_CITY_CAP = 22                  # geographic spread: top-N restaurants / city
TARGET_RESTAURANTS = 360           # final restaurant count (a few hundred)
REVIEWS_PER_RESTAURANT = 140       # most-recent reviews kept per restaurant
TEXT_TRUNCATE = 700                # chars of review text committed to the repo
N_TOPICS = 12
RANDOM_STATE = 42

YELP_SOURCE = "yelp_open_dataset"

# Columns each source contributes so both slices can be concatenated and run
# through the identical scoring / topic / aggregation pipeline.
REV_COLS = ["review_id", "business_id", "date", "stars", "text", "useful", "data_source"]
CHOSEN_COLS = ["business_id", "name", "city", "state", "postal_code", "latitude",
               "longitude", "categories", "stars", "review_count",
               "sampled_reviews", "data_source"]

_WS = re.compile(r"\s+")


def clean_text(t: str) -> str:
    return _WS.sub(" ", (t or "").replace("\n", " ")).strip()


def select_restaurants(biz: pd.DataFrame, rev: pd.DataFrame) -> pd.DataFrame:
    """Pick a few hundred densely-reviewed restaurants with city spread."""
    counts = rev.groupby("business_id").size().rename("sampled_reviews")
    dense = counts[counts >= MIN_REVIEWS_PER_RESTAURANT]
    cand = biz[biz["business_id"].isin(dense.index)].copy()
    cand = cand.merge(dense, on="business_id")

    # Stratify by city so the map is not one metro; keep the busiest per city.
    cand = cand.sort_values("sampled_reviews", ascending=False)
    cand = cand.groupby("city", group_keys=False).head(PER_CITY_CAP)
    cand = cand.sort_values("sampled_reviews", ascending=False).head(TARGET_RESTAURANTS)
    return cand.reset_index(drop=True)


def build_yelp() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Yelp Open Dataset slice: (chosen restaurants, most-recent-N reviews)."""
    print("Loading raw Yelp data ...")
    biz = pd.read_parquet(RAW / "business.parquet")
    biz = biz[biz["categories"].fillna("").str.contains("Restaurants", case=False)]
    rev = pd.read_parquet(RAW / "rest_reviews_subset.parquet")
    rev = rev.dropna(subset=["text"])
    rev = rev[rev["text"].str.len() >= 40]

    chosen = select_restaurants(biz, rev)
    chosen["data_source"] = YELP_SOURCE
    chosen_ids = set(chosen["business_id"])
    print(f"  [yelp] selected {len(chosen)} restaurants across {chosen['city'].nunique()} "
          f"cities / {chosen['state'].nunique()} states.")

    # Keep the most-recent N reviews per chosen restaurant.
    rev = rev[rev["business_id"].isin(chosen_ids)].copy()
    rev["date"] = pd.to_datetime(rev["date"])
    rev = rev.sort_values("date").groupby("business_id", group_keys=False).tail(REVIEWS_PER_RESTAURANT)
    rev["data_source"] = YELP_SOURCE
    return chosen[CHOSEN_COLS].reset_index(drop=True), rev[REV_COLS].reset_index(drop=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Assemble every data source into one restaurant table and one review table.
    # Each source is filtered/sampled independently, then concatenated so the
    # NYC (Google Local) rows run through the exact same scoring / topic model /
    # aggregation as the Yelp rows and land in the same processed artifacts.
    yelp_chosen, yelp_rev = build_yelp()
    print("Loading NYC (Google Local Reviews) data ...")
    nyc_chosen, nyc_rev = load_nyc(RAW)

    frames_c = [yelp_chosen] + ([nyc_chosen] if not nyc_chosen.empty else [])
    frames_r = [yelp_rev] + ([nyc_rev] if not nyc_rev.empty else [])
    chosen = pd.concat(frames_c, ignore_index=True)
    rev = pd.concat(frames_r, ignore_index=True)

    # Re-apply the most-recent-N cap uniformly (idempotent for pre-trimmed sources).
    rev["date"] = pd.to_datetime(rev["date"])
    rev = rev.sort_values("date").groupby("business_id", group_keys=False).tail(REVIEWS_PER_RESTAURANT)
    rev = rev.reset_index(drop=True)
    print(f"Selected {len(chosen)} restaurants across {chosen['city'].nunique()} cities / "
          f"{chosen['state'].nunique()} states / {chosen['data_source'].nunique()} sources.")
    print(f"Scoring {len(rev):,} reviews ...")

    # --- Per-review sentiment + aspects + discrepancy -----------------------
    rev["text"] = rev["text"].map(clean_text)
    rev["sentiment"] = rev["text"].map(sentiment.score_text)
    rev["sentiment_label"] = rev["sentiment"].map(sentiment.label_for_score)
    rev["discrepancy"] = [discrepancy.discrepancy(s, c)
                          for s, c in zip(rev["stars"], rev["sentiment"])]
    rev["discrepancy_flag"] = [discrepancy.flag(s, c)
                               for s, c in zip(rev["stars"], rev["sentiment"])]

    asp_rows = rev["text"].map(aspects.aspect_sentiment)
    for a in aspects.ASPECTS:
        rev[f"aspect_{a}"] = [row[a]["score"] if row[a] else np.nan for row in asp_rows]

    # --- Corpus topic model -------------------------------------------------
    print("Fitting LDA topic model ...")
    tm = topics.fit_topics(rev["text"].tolist(), n_topics=N_TOPICS, random_state=RANDOM_STATE)
    rev["topic_id"] = tm.transform_dominant(rev["text"].tolist()).astype(int)

    topic_records = [
        {"topic_id": i, "label": tm.labels[i], "top_terms": tm.top_terms[i],
         "review_count": int((rev["topic_id"] == i).sum())}
        for i in range(N_TOPICS)
    ]

    # --- Per-restaurant aggregates -----------------------------------------
    print("Aggregating per restaurant ...")
    meta = chosen.set_index("business_id")
    restaurants = []
    for bid, g in rev.groupby("business_id"):
        m = meta.loc[bid]
        g = g.sort_values("date")

        # Monthly sentiment/rating trend for the sparkline.
        gm = g.set_index("date")
        monthly = gm.resample("MS").agg(
            avg_sentiment=("sentiment", "mean"),
            avg_stars=("stars", "mean"),
            review_count=("stars", "size"),
        ).dropna()
        trend = [
            {"month": idx.strftime("%Y-%m"),
             "avg_sentiment": round(float(r.avg_sentiment), 4),
             "avg_stars": round(float(r.avg_stars), 3),
             "count": int(r.review_count)}
            for idx, r in monthly.iterrows()
        ]

        # Aspect summaries.
        aspect_summary = {}
        for a in aspects.ASPECTS:
            col = g[f"aspect_{a}"].dropna()
            aspect_summary[a] = {
                "score": round(float(col.mean()), 4) if len(col) else None,
                "coverage": round(len(col) / len(g), 3),
            }

        # Topic mix for this restaurant.
        tc = g["topic_id"].value_counts(normalize=True)
        top_topics = [
            {"topic_id": int(t), "label": tm.labels[int(t)], "weight": round(float(w), 3)}
            for t, w in tc.head(4).items()
        ]

        # Discrepancy summary.
        disc = {
            "mean_gap": round(float(g["discrepancy"].mean()), 4),
            "pct_positive_text_low_star": round(float((g["discrepancy_flag"] == "positive_text_low_star").mean()), 3),
            "pct_negative_text_high_star": round(float((g["discrepancy_flag"] == "negative_text_high_star").mean()), 3),
        }

        # Pull-quote highlights (short, human-readable).
        short = g[g["text"].str.len().between(60, 320)]
        pos = short.sort_values("sentiment", ascending=False).head(3)
        neg = short.sort_values("sentiment").head(2)

        def quotes(df):
            return [{"text": r.text, "stars": float(r.stars),
                     "sentiment": round(float(r.sentiment), 3),
                     "date": r.date.strftime("%Y-%m-%d")} for r in df.itertuples()]

        restaurants.append({
            "business_id": bid,
            "name": m["name"],
            "city": m["city"],
            "state": m["state"],
            "postal_code": m["postal_code"],
            "latitude": float(m["latitude"]),
            "longitude": float(m["longitude"]),
            "categories": [c.strip() for c in str(m["categories"]).split(",")
                           if c.strip() and c.strip().lower() != "restaurants"][:6],
            "data_source": m["data_source"],
            "platform_stars": float(m["stars"]),
            "platform_review_count": int(m["review_count"]),
            "sampled_reviews": int(len(g)),
            "avg_stars": round(float(g["stars"].mean()), 3),
            "avg_sentiment": round(float(g["sentiment"].mean()), 4),
            "pct_positive": round(float((g["sentiment_label"] == "positive").mean()), 3),
            "pct_negative": round(float((g["sentiment_label"] == "negative").mean()), 3),
            "first_review": g["date"].min().strftime("%Y-%m-%d"),
            "last_review": g["date"].max().strftime("%Y-%m-%d"),
            "aspects": aspect_summary,
            "trend": trend,
            "top_topics": top_topics,
            "discrepancy": disc,
            "highlights": {"positive": quotes(pos), "negative": quotes(neg)},
        })

    restaurants.sort(key=lambda r: r["sampled_reviews"], reverse=True)

    # --- Write artifacts ----------------------------------------------------
    keep_cols = ["review_id", "business_id", "date", "stars", "sentiment",
                 "sentiment_label", "discrepancy", "discrepancy_flag", "topic_id",
                 "useful", "data_source"] + [f"aspect_{a}" for a in aspects.ASPECTS]
    rev_out = rev[keep_cols + ["text"]].copy()
    rev_out["text"] = rev_out["text"].str.slice(0, TEXT_TRUNCATE)
    rev_out.to_parquet(OUT / "reviews.parquet", index=False)

    (OUT / "restaurants.json").write_text(json.dumps(restaurants, ensure_ascii=False))
    (OUT / "topics.json").write_text(json.dumps(topic_records, ensure_ascii=False, indent=2))

    source_counts = {s: int((chosen["data_source"] == s).sum())
                     for s in sorted(chosen["data_source"].unique())}
    meta_out = {
        "source": "Yelp Open Dataset + UCSD Google Local Reviews (NYC)",
        "business_source": "yashraizada/yelp-open-dataset-business",
        "review_source": "seansanchez951/yelp_academic_dataset_review",
        "data_sources": {
            "yelp_open_dataset": {
                "label": "Yelp Open Dataset",
                "provenance": "Yelp Open Dataset via Hugging Face mirrors "
                              "(yashraizada/yelp-open-dataset-business + "
                              "seansanchez951/yelp_academic_dataset_review)",
                "restaurants": source_counts.get(YELP_SOURCE, 0),
            },
            "google_local_reviews": {
                "label": "Google Local Reviews (NYC)",
                "provenance": "UCSD/McAuley 'Google Local' dataset (2021), "
                              "New York state slice, filtered to the five boroughs "
                              "(mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal)",
                "restaurants": source_counts.get("google_local_reviews", 0),
            },
        },
        "restaurants": len(restaurants),
        "reviews": int(len(rev)),
        "cities": int(chosen["city"].nunique()),
        "states": int(chosen["state"].nunique()),
        "date_range": [rev["date"].min().strftime("%Y-%m-%d"),
                       rev["date"].max().strftime("%Y-%m-%d")],
        "sentiment_model": "VADER (vaderSentiment)",
        "topic_model": f"sklearn LDA, {N_TOPICS} topics",
        "aspects": list(aspects.ASPECTS.keys()),
        "sampling": {
            "min_reviews_per_restaurant": MIN_REVIEWS_PER_RESTAURANT,
            "per_city_cap": PER_CITY_CAP,
            "reviews_per_restaurant": REVIEWS_PER_RESTAURANT,
        },
    }
    (OUT / "meta.json").write_text(json.dumps(meta_out, indent=2))

    print("\nDone.")
    print(f"  restaurants : {len(restaurants)} ({source_counts})")
    print(f"  reviews     : {len(rev):,}")
    print(f"  cities      : {chosen['city'].nunique()} / states {chosen['state'].nunique()}")
    for f in ["reviews.parquet", "restaurants.json", "topics.json", "meta.json"]:
        print(f"  {f:18} {(OUT / f).stat().st_size / 1e6:6.2f} MB")


if __name__ == "__main__":
    main()
