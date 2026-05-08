"""Dependency-free local retriever for real XHS reference posts."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SAMPLE_ARTICLES_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_articles.json"
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_SPEC_RE = re.compile(r"[a-zA-Z]+[0-9,.]*|[0-9,.]+(?:mm|cm|lm|lx|㎡|平米|k)?|Ra\d+|RG\d+", re.IGNORECASE)


@dataclass(frozen=True)
class ArticlePost:
    """A real reference post loaded from the local sample article corpus."""

    id: str
    title: str
    source: str
    content: str

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.content}"


@dataclass(frozen=True)
class RetrievedPost:
    """A retrieved post with a similarity score."""

    id: str
    title: str
    source: str
    content: str
    score: float

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.content}"


class SampleArticleStore:
    """Loads real post examples from JSON."""

    def __init__(self, path: str | Path = DEFAULT_SAMPLE_ARTICLES_PATH) -> None:
        self.path = Path(path)

    def load(self) -> list[ArticlePost]:
        with self.path.open("r", encoding="utf-8") as file:
            rows = json.load(file)
        return [
            ArticlePost(
                id=str(row["id"]),
                title=str(row["title"]),
                source=str(row["source"]),
                content=str(row["content"]),
            )
            for row in rows
        ]


class LocalArticleRetriever:
    """Ranks local articles by cosine similarity over Chinese n-grams and specs."""

    def __init__(self, articles: Iterable[ArticlePost] | None = None) -> None:
        self.articles = list(articles) if articles is not None else SampleArticleStore().load()
        self._article_vectors = [(article, self.vectorize(article.text)) for article in self.articles]

    def retrieve(self, query: str, top_k: int = 2) -> list[RetrievedPost]:
        query_vector = self.vectorize(query)
        if not query_vector:
            return []

        ranked = []
        for article, vector in self._article_vectors:
            score = self.cosine(query_vector, vector)
            ranked.append((score, article))

        ranked.sort(key=lambda item: (item[0], self._geo_priority(item[1])), reverse=True)
        return [
            RetrievedPost(
                id=article.id,
                title=article.title,
                source=article.source,
                content=article.content,
                score=round(score, 4),
            )
            for score, article in ranked[:top_k]
            if score > 0
        ]

    @classmethod
    def vectorize(cls, text: str) -> Counter[str]:
        normalized = cls.normalize(text)
        tokens: list[str] = []
        cjk_chars = "".join(_CJK_RE.findall(normalized))

        for size in (2, 3):
            tokens.extend(cjk_chars[index : index + size] for index in range(max(0, len(cjk_chars) - size + 1)))

        tokens.extend(match.group(0).lower().replace(",", "") for match in _LATIN_SPEC_RE.finditer(normalized))
        tokens.extend(cls._keyword_tokens(normalized))
        return Counter(token for token in tokens if token.strip())

    @staticmethod
    def normalize(text: str) -> str:
        return (
            text.lower()
            .replace("，", " ")
            .replace("。", " ")
            .replace("！", " ")
            .replace("？", " ")
            .replace(",", "")
            .replace("~", "")
            .replace("约", "")
        )

    @staticmethod
    def cosine(left: Counter[str], right: Counter[str]) -> float:
        shared = set(left) & set(right)
        numerator = sum(left[token] * right[token] for token in shared)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    @staticmethod
    def _keyword_tokens(text: str) -> list[str]:
        keywords = [
            "客厅",
            "卧室",
            "儿童房",
            "护眼",
            "揉眼睛",
            "超薄",
            "不压层高",
            "吸顶灯",
            "米家",
            "小米",
            "全光谱",
            "柔光",
            "智能",
            "原木风",
            "韩系",
            "聚会",
            "写作业",
            "居家办公",
            "l100",
            "d60",
            "d50",
            "10000lm",
            "14.5mm",
            "ra98",
            "rg0",
        ]
        return [keyword for keyword in keywords if keyword in text]

    @staticmethod
    def _geo_priority(article: ArticlePost) -> int:
        return 1 if article.id.startswith("geo_") else 0

