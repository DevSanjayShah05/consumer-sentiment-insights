"""Corpus-level topic modelling with Latent Dirichlet Allocation (LDA).

We vectorise the review corpus with a bag-of-words ``CountVectorizer`` (English
stop-words, unigrams + bigrams, aggressive min/max document-frequency pruning)
and fit an ``sklearn`` ``LatentDirichletAllocation`` model. Each review is then
assigned its dominant topic, and every topic is given a human-readable label
via a curated keyword->theme mapping (falling back to its top terms).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

# Curated themes: if a topic's top terms intersect a theme's cue words, we adopt
# that theme's label. Ordered by specificity.
THEME_CUES: List[Tuple[str, List[str]]] = [
    ("Wait Times & Reservations", ["wait", "minutes", "reservation", "line", "hour", "seated", "table"]),
    ("Service & Staff", ["service", "staff", "server", "waiter", "waitress", "friendly", "rude", "manager"]),
    ("Value & Pricing", ["price", "worth", "expensive", "cheap", "value", "money", "cost", "portion"]),
    ("Ambiance & Decor", ["atmosphere", "ambiance", "decor", "music", "patio", "cozy", "vibe", "seating"]),
    ("Breakfast & Brunch", ["breakfast", "brunch", "eggs", "pancakes", "coffee", "bacon", "waffle"]),
    ("Pizza & Italian", ["pizza", "crust", "italian", "pasta", "sauce", "cheese", "slice"]),
    ("Sushi & Japanese", ["sushi", "roll", "ramen", "japanese", "sashimi", "rice", "tempura"]),
    ("Mexican & Tacos", ["taco", "burrito", "salsa", "mexican", "guacamole", "chips", "margarita"]),
    ("Burgers & Bar Food", ["burger", "fries", "beer", "bar", "wings", "sandwich", "fried"]),
    ("BBQ & Meats", ["bbq", "brisket", "ribs", "pork", "smoked", "meat", "barbecue"]),
    ("Desserts & Bakery", ["dessert", "cake", "ice cream", "sweet", "chocolate", "bakery", "donut"]),
    ("Drinks & Cocktails", ["drink", "cocktail", "wine", "happy hour", "bartender", "beer", "coffee"]),
    ("Cleanliness & Hygiene", ["clean", "dirty", "bathroom", "health", "hygiene", "gross"]),
]

STOP_EXTRA = {
    "place", "food", "restaurant", "order", "ordered", "got", "went", "came",
    "definitely", "really", "just", "like", "good", "great", "time", "back",
    "did", "didn", "ve", "don", "ll",
}


@dataclass
class TopicModel:
    vectorizer: CountVectorizer
    lda: LatentDirichletAllocation
    top_terms: List[List[str]] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)

    def transform_dominant(self, texts: List[str]) -> np.ndarray:
        """Return the dominant topic id for each text."""
        doc_topic = self.lda.transform(self.vectorizer.transform(texts))
        return doc_topic.argmax(axis=1)


def _label_topic(terms: List[str], used: set) -> str:
    term_set = set(terms)
    for label, cues in THEME_CUES:
        if label in used:
            continue
        if term_set & set(cues):
            return label
    # Fallback: title-case the three most salient terms.
    return " / ".join(t.title() for t in terms[:3])


def fit_topics(texts: List[str], n_topics: int = 12, n_top_terms: int = 10,
               random_state: int = 42) -> TopicModel:
    """Fit an LDA topic model over ``texts`` and derive readable labels."""
    stop_words = list(CountVectorizer(stop_words="english").get_stop_words() | STOP_EXTRA)
    vectorizer = CountVectorizer(
        stop_words=stop_words,
        ngram_range=(1, 2),
        min_df=25,
        max_df=0.35,
        max_features=8000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
    )
    dtm = vectorizer.fit_transform(texts)
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        learning_method="online",
        max_iter=15,
        random_state=random_state,
        n_jobs=-1,
    )
    lda.fit(dtm)

    vocab = np.array(vectorizer.get_feature_names_out())
    top_terms: List[List[str]] = []
    labels: List[str] = []
    used: set = set()
    for comp in lda.components_:
        idx = comp.argsort()[::-1][:n_top_terms]
        terms = list(vocab[idx])
        label = _label_topic(terms, used)
        used.add(label)
        top_terms.append(terms)
        labels.append(label)

    return TopicModel(vectorizer=vectorizer, lda=lda, top_terms=top_terms, labels=labels)
