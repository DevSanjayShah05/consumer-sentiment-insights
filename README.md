# Tablecloth

**Consumer review & sentiment intelligence for restaurants.**

Tablecloth mines a sampled slice of real Yelp restaurant reviews to surface what
star ratings alone hide: sentiment trends over time, aspect-level opinion on
food / service / price / ambiance, the themes people actually write about, and
the restaurants where the text and the star rating tell different stories.

It's built as a portfolio piece for consumer-analyst / consumer-insights work —
the goal is an analyst tool that reads like a real internal product, not a
tutorial demo: a light, warm, editorial visual identity; transparent,
inspectable methodology (no black-box scores); and REST endpoints shaped the
way an analytics team would actually consume them (browse/filter, single-entity
detail, side-by-side comparison, cross-entity aggregation).

---

## What it does

- **Restaurant explorer** — card-based browsing across ~360 restaurants, filterable
  by state, cuisine/category, rating, and by two "discrepancy" lenses: *hidden
  gems* (text reads warmer than the star rating) and *overrated* (text reads
  harsher than the star rating).
- **Restaurant detail** — monthly sentiment trend, a four-aspect sentiment
  breakdown (food / service / price / ambiance), the restaurant's dominant
  discussion topics, and pull-quote highlights pulled from the most positive
  and most negative reviews.
- **Comparison mode** — any two restaurants side by side: headline metrics,
  overlaid sentiment trend, aspect bars, and topic mix.

All of the NLP (sentiment, aspects, topics, discrepancy) runs **offline**, once,
via `backend/build_dataset.py`. The API only serves pre-computed derived data —
so it starts instantly and every request is a cheap in-memory lookup.

---

## Data sources & sampling

**Underlying dataset:** the [Yelp Open Dataset](https://www.yelp.com/dataset)
(academic/non-commercial use), accessed via two directly-downloadable,
credential-free Hugging Face mirrors (no manual TOS click-through required to
fetch programmatically):

| Artifact | Source | What it provides |
|---|---|---|
| Business metadata | [`yashraizada/yelp-open-dataset-business`](https://huggingface.co/datasets/yashraizada/yelp-open-dataset-business) | name, city/state/postal code, lat/lon, categories, Yelp's own star rating & review count |
| Review text | [`seansanchez951/yelp_academic_dataset_review`](https://huggingface.co/datasets/seansanchez951/yelp_academic_dataset_review) | review text, star rating, date, `useful` votes (accessed via HF's auto-converted Parquet shards) |

Joined on `business_id`.

**Filtering & sampling** (see `backend/build_dataset.py` for the exact code):

1. Businesses filtered to `categories` containing `"Restaurants"`.
2. Four of the ten review Parquet shards were downloaded (~1.25 GB of the ~3.2 GB
   corpus) and filtered to restaurant `business_id`s — **1,971,657** candidate
   restaurant reviews across ~25,000 restaurants. Downloading all ten shards
   was unnecessary for a representative, tractable sample.
3. Restaurants were kept only if they had **≥100 reviews** within that sample
   (a density floor so per-restaurant trend/aspect/topic numbers aren't noise),
   then **capped at 22 restaurants per city** to force geographic spread rather
   than let a handful of dense metros dominate, then the **360** busiest
   survivors were kept.
4. For each of those restaurants, the **140 most recent** reviews were kept.

**Result:** **360 restaurants**, **50,400 reviews**, **82 cities across 14
US/Canadian states/provinces**, reviews spanning **2015-09 to 2022-01**. This
sits inside the ~20k–60k review / few-hundred-restaurant target for a build
that's tractable to develop against while still being a real, representative
corpus rather than a synthetic toy.

Raw downloaded Parquet (~2 GB) is **not** committed — it's gitignored
(`backend/data/raw/`). What *is* committed is the small **derived** dataset the
app actually reads: `backend/data/processed/` — `reviews.parquet` (scored
reviews, ~14 MB), `restaurants.json` (per-restaurant aggregates, ~2 MB),
`topics.json`, and `meta.json`. Total committed data footprint: **~15 MB**.

To regenerate the derived data from scratch (optional — not required to run the
app, since the derived artifacts are already committed):

```bash
cd backend
# download business.parquet + the review shards you want into data/raw/
# (see the two HF dataset links above)
python build_dataset.py
```

---

## Methodology

| Step | Approach | Why |
|---|---|---|
| **Sentiment** | [VADER](https://github.com/cjhutto/vaderSentiment) (`vaderSentiment`) compound score, `[-1, 1]`, on full review text | Lexicon/rule-based, deterministic, fast, no GPU — appropriate for a bounded 50k-review batch job, and its `[-1,1]` output is directly comparable to a normalized star rating |
| **Aspect sentiment** | Keyword-anchored: split each review into sentences, tag sentences that mention curated `food` / `service` / `price` / `ambiance` anchor terms, average VADER sentiment over the matching sentences per aspect | Transparent and inspectable — every aspect score traces back to specific sentences and specific matched words, no training data required |
| **Topic modeling** | `sklearn` `CountVectorizer` (uni+bigrams, English + domain stopwords, `min_df=25`, `max_df=0.35`) → `LatentDirichletAllocation`, 12 topics, dominant topic per review | Unsupervised, corpus-native themes; topics are given human-readable labels via a curated keyword→theme lookup (e.g. "wait", "reservation", "line" → *Wait Times & Reservations*), falling back to top terms when no theme matches |
| **Rating/sentiment discrepancy** | Star rating mapped onto the same `[-1,1]` scale as sentiment (`(stars − 3) / 2`); `gap = sentiment − normalized_stars`; flagged as `positive_text_low_star` / `negative_text_high_star` when `|gap| ≥ 0.6` | Surfaces the cases a headline star average hides — glowing text under a low score, or critical text under a 5-star rating |
| **Geo / time aggregation** | Per-restaurant monthly resample (avg sentiment, avg stars, review count) for trend charts; corpus-wide `/api/geo` (by city) and `/api/trend` (by month) for cross-restaurant views | |

All four steps run once in `backend/build_dataset.py`; the API never re-runs NLP
at request time.

**Limitations to be upfront about:** keyword-anchored aspect extraction is a
heuristic, not a trained aspect-based-sentiment model, so it can mis-attribute
sentences with ambiguous wording; LDA topics are unsupervised and occasionally
produce a noisy or overlapping label; VADER is lexicon-based and weaker on
sarcasm and complex negation than a transformer model would be; this is a
360-restaurant sample of a much larger corpus, not the full Yelp dataset.

---

## Architecture

```
backend/
  analysis/            sentiment.py, aspects.py, topics.py, discrepancy.py
                        — the four NLP modules, unit-testable in isolation
  build_dataset.py      offline pipeline: raw Yelp data -> scored reviews,
                         per-restaurant aggregates, topic model -> data/processed/
  app/
    data_store.py        loads data/processed/ once at startup
    main.py               FastAPI app + REST routes (read-only, in-memory)
  data/
    raw/                 gitignored — raw downloaded Yelp Parquet
    processed/            committed — the small derived dataset the API serves

frontend/
  src/
    api/                 typed fetch client + response types
    components/           RestaurantCard, AspectBars, TrendChart, Sparkline,
                           PullQuote, TopicChips, FilterBar, Layout
    pages/                 Explorer, RestaurantDetail, Compare
    styles/                theme.css (design tokens) + components.css
```

**Backend:** FastAPI, pandas/pyarrow for the offline pipeline, scikit-learn for
LDA, VADER for sentiment. Endpoints: `/api/restaurants` (list/filter/sort),
`/api/restaurants/{id}` (detail), `/api/restaurants/{id}/reviews` (paginated
drilldown), `/api/compare?a=&b=`, `/api/topics`, `/api/geo`, `/api/trend`,
`/api/filters`, `/api/meta`, `/api/health`.

**Frontend:** React + TypeScript + Vite, React Router, Recharts for the trend
charts. Visual identity is a deliberate departure from a dark analytics
dashboard: a light, warm, editorial/magazine aesthetic — serif (Fraunces)
headlines, a warm-neutral ivory page plane, generous whitespace, and a
categorical/sequential/diverging color system (rust / gold / plum / green,
validated for lightness, chroma, and colorblind-safe adjacent-pair separation)
in place of a generic dashboard palette.

---

## Setup & run

Requires Python 3.11+ and Node 20+.

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# -> http://127.0.0.1:8000/api/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# -> http://localhost:5173 (proxies /api/* to http://127.0.0.1:8000 in dev)
```

Production build:

```bash
cd frontend
npm run build   # outputs frontend/dist/
```

The frontend calls a relative `/api` base by default (`VITE_API_URL` env var to
override) — deploying it behind the same host/reverse proxy as the FastAPI app
is the simplest path; a split deployment needs `VITE_API_URL` pointed at the
API's public URL and CORS is already open (`allow_origins=["*"]`) for that case.

---

## Screenshots

_Add screenshots of the Explorer, Restaurant Detail, and Compare views here
after running the app locally — none are committed yet._

---

## Status / TODOs

- No authentication, rate limiting, or production deployment config — this is
  built to be run locally or deployed behind a reverse proxy of the operator's
  choosing.
- Aspect and topic models are heuristic/unsupervised; a fine-tuned ABSA model
  or a supervised topic taxonomy would sharpen both.
- Only a 360-restaurant sample is included; the pipeline generalizes to more
  shards of the same corpus if a larger sample is wanted later.
