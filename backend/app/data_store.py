"""Loads the derived Tablecloth artifacts once at process startup.

The API never touches the raw Yelp data or re-runs NLP at request time — all
heavy lifting happened offline in ``build_dataset.py``. This module just reads
the small derived JSON/Parquet artifacts into memory and exposes convenient
lookup structures for the route handlers in ``main.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


class DataStore:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.restaurants: List[dict] = json.loads((data_dir / "restaurants.json").read_text())
        self.topics: List[dict] = json.loads((data_dir / "topics.json").read_text())
        self.meta: dict = json.loads((data_dir / "meta.json").read_text())
        self.reviews: pd.DataFrame = pd.read_parquet(data_dir / "reviews.parquet")

        self._by_id: Dict[str, dict] = {r["business_id"]: r for r in self.restaurants}
        self.cities: List[str] = sorted({r["city"] for r in self.restaurants})
        self.states: List[str] = sorted({r["state"] for r in self.restaurants})
        cats = set()
        for r in self.restaurants:
            cats.update(r["categories"])
        self.categories: List[str] = sorted(cats)

    def get(self, business_id: str) -> Optional[dict]:
        return self._by_id.get(business_id)

    def reviews_for(self, business_id: str, limit: Optional[int] = None) -> pd.DataFrame:
        df = self.reviews[self.reviews["business_id"] == business_id].sort_values(
            "date", ascending=False
        )
        if limit:
            df = df.head(limit)
        return df


_store: Optional[DataStore] = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store
