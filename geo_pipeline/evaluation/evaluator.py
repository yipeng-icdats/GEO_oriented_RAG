"""Rubric-based evaluator for GEO social posts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from geo_pipeline.prompts.geo_prompt import PromptGenerationRequest


@dataclass(frozen=True)
class RubricScore:
    """A single rubric dimension scored from 0 to 5."""

    name: str
    score: float
    rationale: str


@dataclass(frozen=True)
class EvaluationResult:
    """Scorecard for a generated social post."""

    overall_score: float
    passed: bool
    scores: list[RubricScore]
    recommendations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "overall_score": self.overall_score,
            "passed": self.passed,
            "scores": [score.__dict__ for score in self.scores],
            "recommendations": self.recommendations,
        }


class GEOEvaluator:
    """Lightweight deterministic evaluator for early prompt iteration.

    The evaluator is intentionally transparent. It provides a fast local signal
    before later refinement with LLM-as-judge, human review, or live metrics.
    """

    promotional_cliches = {
        "game changer",
        "revolutionary",
        "best-in-class",
        "must-have",
        "limited time",
        "buy now",
        "act now",
        "unlock your potential",
        "transform your life",
    }
    human_markers = {
        "i ",
        "we ",
        "you ",
        "today",
        "honestly",
        "noticed",
        "started",
        "learned",
        "because",
        "when",
    }

    def __init__(self, pass_threshold: float = 3.7) -> None:
        self.pass_threshold = pass_threshold

    def evaluate(
        self,
        post: str,
        request: PromptGenerationRequest | None = None,
        reference_facts: Iterable[str] | None = None,
    ) -> EvaluationResult:
        normalized = self._normalize(post)
        facts = list(reference_facts or [])
        if request:
            facts.extend(self._facts_from_request(request))

        scores = [
            self._score_naturalness(post, normalized),
            self._score_brand_fit(normalized, request),
            self._score_product_integration(normalized, request),
            self._score_grounding(normalized, facts),
            self._score_engagement(post, normalized),
            self._score_compliance(post, normalized, request),
        ]
        overall = round(sum(score.score for score in scores) / len(scores), 2)
        recommendations = self._recommend(scores)
        return EvaluationResult(
            overall_score=overall,
            passed=overall >= self.pass_threshold and not self._has_zero(scores),
            scores=scores,
            recommendations=recommendations,
        )

    def _score_naturalness(self, post: str, normalized: str) -> RubricScore:
        score = 3.0
        if any(marker in normalized for marker in self.human_markers):
            score += 0.8
        if 25 <= len(post.split()) <= 180:
            score += 0.6
        if any(cliche in normalized for cliche in self.promotional_cliches):
            score -= 1.0
        if normalized.count("!") > 2:
            score -= 0.4
        return RubricScore("naturalness", self._bound(score), "Assesses conversational tone, length, and hype.")

    def _score_brand_fit(
        self, normalized: str, request: PromptGenerationRequest | None
    ) -> RubricScore:
        if not request:
            return RubricScore("brand_fit", 3.0, "No request supplied, so brand fit cannot be fully checked.")

        brand = request.brand
        score = 2.5
        if brand.name.lower() in normalized:
            score += 1.0
        voice_hits = sum(1 for item in brand.voice if item.lower() in normalized)
        if brand.voice and voice_hits:
            score += min(1.0, voice_hits * 0.5)
        if all(term.lower() in normalized for term in brand.required_terms):
            score += 0.8
        if any(claim.lower() in normalized for claim in brand.prohibited_claims):
            score -= 2.0
        return RubricScore("brand_fit", self._bound(score), "Checks brand mention, requested voice cues, and restricted claims.")

    def _score_product_integration(
        self, normalized: str, request: PromptGenerationRequest | None
    ) -> RubricScore:
        if not request:
            return RubricScore("product_integration", 3.0, "No request supplied, so product fit cannot be fully checked.")

        product = request.product
        facts = [product.name, product.category, *product.key_features, *product.differentiators, *product.use_cases]
        hit_count = sum(1 for fact in facts if self._contains_key_terms(normalized, fact))
        score = 2.0
        if product.name.lower() in normalized:
            score += 1.0
        score += min(2.0, hit_count * 0.45)
        if hit_count == 0:
            score -= 1.0
        return RubricScore("product_integration", self._bound(score), "Measures whether product facts appear naturally and specifically.")

    def _score_grounding(self, normalized: str, facts: list[str]) -> RubricScore:
        if not facts:
            return RubricScore("factual_grounding", 3.0, "No reference facts supplied.")

        supported_hits = sum(1 for fact in facts if self._contains_key_terms(normalized, fact))
        score = 2.5 + min(2.0, supported_hits * 0.35)
        suspicious_patterns = [
            r"\b\d+x\b",
            r"\b100%\b",
            r"\bguaranteed\b",
            r"\bclinically proven\b",
            r"\b#1\b",
        ]
        if any(re.search(pattern, normalized) for pattern in suspicious_patterns):
            score -= 1.0
        return RubricScore("factual_grounding", self._bound(score), "Rewards use of provided facts and penalizes unsupported superlatives.")

    def _score_engagement(self, post: str, normalized: str) -> RubricScore:
        score = 2.8
        if "?" in post:
            score += 0.5
        if any(word in normalized for word in ["try", "share", "see", "learn", "tell", "visit"]):
            score += 0.6
        if len(post.split()) < 35:
            score -= 0.5
        if len(post.split()) > 220:
            score -= 0.7
        if "#" in post:
            score += 0.3
        return RubricScore("engagement", self._bound(score), "Looks for audience invitation, readable length, and light discoverability.")

    def _score_compliance(
        self,
        post: str,
        normalized: str,
        request: PromptGenerationRequest | None,
    ) -> RubricScore:
        score = 4.0
        if request and len(post.split()) > request.max_words:
            score -= 1.3
        if request and not request.include_hashtags and "#" in post:
            score -= 0.8
        if any(cliche in normalized for cliche in self.promotional_cliches):
            score -= 0.7
        if request and any(claim.lower() in normalized for claim in request.brand.prohibited_claims):
            score = 0.0
        return RubricScore("compliance", self._bound(score), "Checks explicit generation constraints and obvious ad-safety issues.")

    def _recommend(self, scores: list[RubricScore]) -> list[str]:
        messages = {
            "naturalness": "Make the post more conversational and less promotional.",
            "brand_fit": "Add clearer brand cues without repeating the brand name too often.",
            "product_integration": "Use a specific product feature or use case instead of generic benefits.",
            "factual_grounding": "Anchor claims in the provided evidence and remove unsupported superlatives.",
            "engagement": "Add a light audience hook, question, or context-specific call to action.",
            "compliance": "Tighten the post against length, hashtag, claim, and policy constraints.",
        }
        return [messages[score.name] for score in scores if score.score < 3.5]

    def _facts_from_request(self, request: PromptGenerationRequest) -> list[str]:
        product = request.product
        return [
            request.brand.name,
            product.name,
            product.category,
            *product.key_features,
            *product.differentiators,
            *product.proof_points,
            *product.use_cases,
            *request.evidence,
        ]

    def _contains_key_terms(self, normalized: str, fact: str) -> bool:
        terms = [term for term in re.findall(r"[a-z0-9]+", fact.lower()) if len(term) > 3]
        if not terms:
            return False
        needed = 1 if len(terms) <= 2 else 2
        return sum(1 for term in terms if term in normalized) >= needed

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    def _bound(self, value: float) -> float:
        return round(max(0.0, min(5.0, value)), 2)

    def _has_zero(self, scores: list[RubricScore]) -> bool:
        return any(score.score == 0.0 for score in scores)

