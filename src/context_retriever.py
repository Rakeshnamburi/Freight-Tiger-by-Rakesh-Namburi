"""Deterministic TF-IDF retrieval over the supplied context notes."""

from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ContextRetriever:
    def __init__(self, notes: pd.DataFrame) -> None:
        self.notes = notes.copy().reset_index(drop=True)
        documents = self.notes.apply(self._document_text, axis=1).tolist()
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.note_matrix = self.vectorizer.fit_transform(documents)

    @staticmethod
    def _document_text(note: pd.Series) -> str:
        date = pd.Timestamp(note["date"])
        return (
            f"{note['applies_to']} {date:%Y-%m-%d} {date:%B} "
            f"transportation freight cost increase {note['note']}"
        )

    @staticmethod
    def build_query(observation: pd.Series) -> str:
        week = pd.Timestamp(observation["week_of"])
        return (
            f"{observation['route']} {observation['route_type']} {week:%Y-%m-%d} "
            f"{week:%B} transportation freight cost increase surcharge fuel toll "
            "weather disruption"
        )

    def retrieve(self, observation: pd.Series, top_k: int = 5) -> pd.DataFrame:
        query_vector = self.vectorizer.transform([self.build_query(observation)])
        scores = cosine_similarity(query_vector, self.note_matrix).ravel()
        ranked = self.notes.copy()
        ranked["retrieval_score"] = scores
        ranked = ranked.sort_values(
            ["retrieval_score", "note_id"],
            ascending=[False, True],
            kind="mergesort",
        )
        return ranked.head(min(top_k, len(ranked))).reset_index(drop=True)

