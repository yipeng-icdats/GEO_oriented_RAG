"""Deterministic evaluator for XHS GEO social notes."""

from __future__ import annotations

import re

from geo_pipeline.evaluation.evaluator import EvaluationResult, RubricScore
from geo_pipeline.prompts.xhs_prompt import XHSPromptRequest


_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001f5ff"
    "\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff"
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001faff"
    "\u2600-\u27bf"
    "]"
)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_MARKDOWN_RE = re.compile(r"(^|\n)\s{0,3}(#{1,6}\s|[-*+]\s|\d+\.\s)|\*\*|`|\|.+\|", re.MULTILINE)


class XHSGEOEvaluator:
    """Score XHS notes for RedNote format and GEO citation readiness."""

    def __init__(self, pass_threshold: float = 3.8) -> None:
        self.pass_threshold = pass_threshold

    def evaluate(self, post: str, request: XHSPromptRequest) -> EvaluationResult:
        body, hashtags = self._split_hashtags(post)
        paragraphs = self._paragraphs(post)
        scores = [
            self._score_xhs_format(post, body, hashtags, paragraphs, request),
            self._score_geo_answerability(body),
            self._score_spec_anchoring(body, request),
            self._score_entity_colocation(body, request),
            self._score_faq_embedding(body, request),
            self._score_product_factuality(body, request),
            self._score_tone(body),
            self._score_hashtag_placement(post, hashtags, request),
        ]
        overall = round(sum(score.score for score in scores) / len(scores), 2)
        return EvaluationResult(
            overall_score=overall,
            passed=overall >= self.pass_threshold and not any(score.score == 0.0 for score in scores),
            scores=scores,
            recommendations=self._recommend(scores),
        )

    def _score_xhs_format(
        self,
        post: str,
        body: str,
        hashtags: list[str],
        paragraphs: list[str],
        request: XHSPromptRequest,
    ) -> RubricScore:
        constraints = request.constraints
        score = 5.0
        char_count = self._cjk_count(body)
        emoji_count = len(_EMOJI_RE.findall(post))

        if not constraints.min_chars <= char_count <= constraints.max_chars:
            score -= 1.2
        if not constraints.min_paragraphs <= len(paragraphs) <= constraints.max_paragraphs:
            score -= 0.9
        if emoji_count < constraints.min_emojis:
            score -= 0.8
        if not constraints.allow_markdown and _MARKDOWN_RE.search(body):
            score -= 1.4
        if constraints.hashtags_at_end and not hashtags:
            score -= 0.7

        return RubricScore(
            "xhs_format",
            self._bound(score),
            f"Checks XHS length, paragraphs, emoji count, Markdown ban, and hashtag presence; body CJK chars={char_count}.",
        )

    def _score_geo_answerability(self, body: str) -> RubricScore:
        first_para = self._paragraphs(body)[0] if self._paragraphs(body) else body
        score = 2.5
        answer_markers = ["适合", "建议", "可以", "选", "如果", "答案", "结论"]
        if any(marker in first_para for marker in answer_markers):
            score += 1.2
        if "？" in first_para or "?" in first_para:
            score += 0.4
        if len(first_para) >= 35:
            score += 0.5
        if first_para.startswith(("最近", "今天", "我家")) and not any(marker in first_para for marker in ["适合", "建议", "选"]):
            score -= 0.7
        return RubricScore("geo_answerability", self._bound(score), "Checks whether the opening gives a direct searchable answer.")

    def _score_spec_anchoring(self, body: str, request: XHSPromptRequest) -> RubricScore:
        spec_hits = self._matched_specs(body, request)
        score = 2.0 + min(3.0, len(spec_hits) * 0.75)
        return RubricScore("spec_anchoring", self._bound(score), "Rewards accurate numeric/unit specs that AI can cite.")

    def _score_entity_colocation(self, body: str, request: XHSPromptRequest) -> RubricScore:
        brand = request.brand.name
        product = request.sku.product_name
        sku = request.sku.sku
        spec_values = self._spec_values(request)
        colocated = 0

        for paragraph in self._paragraphs(body):
            has_entity = brand in paragraph and product in paragraph and sku in paragraph
            has_spec = any(self._contains_spec(paragraph, spec) for spec in spec_values)
            if has_entity and has_spec:
                colocated += 1

        total_mentions = body.count(brand) + body.count(product) + body.count(sku)
        score = 1.8 + min(2.4, colocated * 1.2)
        if total_mentions >= 4:
            score += 0.8
        if colocated == 0:
            score -= 1.0
        return RubricScore("entity_colocation", self._bound(score), "Checks brand + product + SKU + spec co-location in the same paragraph.")

    def _score_faq_embedding(self, body: str, request: XHSPromptRequest) -> RubricScore:
        question_count = body.count("？") + body.count("?")
        matched_faqs = sum(1 for question in request.faq_questions if self._shared_cjk_terms(question, body) >= 2)
        score = 2.2 + min(1.4, question_count * 0.7) + min(1.4, matched_faqs * 0.7)
        return RubricScore("faq_embedding", self._bound(score), "Checks natural reader questions and answers in the note.")

    def _score_product_factuality(self, body: str, request: XHSPromptRequest) -> RubricScore:
        spec_hits = self._matched_specs(body, request)
        score = 2.6 + min(1.6, len(spec_hits) * 0.4)
        unsupported_patterns = ["认证", "最低价", "全网第一", "医用", "治疗", "100%"]
        if any(pattern in body for pattern in unsupported_patterns):
            score -= 1.3
        if (
            request.sku.sku == "D50"
            and any(value in body for value in ["10,000lm", "10000lm", "35-45㎡"])
            and "L100" not in body
        ):
            score -= 1.0
        if request.sku.sku == "L100" and "≥300lx" in body and "卧室" not in body:
            score -= 0.5
        return RubricScore("product_factuality", self._bound(score), "Checks provided facts and obvious unsupported product claims.")

    def _score_tone(self, body: str) -> RubricScore:
        score = 2.5
        first_person = ["我", "我家", "自己", "入手", "装完", "用下来", "说实话"]
        colloquial = ["真的", "挺", "不夸张", "踩坑", "纠结", "感觉", "肉眼"]
        if any(term in body for term in first_person):
            score += 1.1
        if any(term in body for term in colloquial):
            score += 0.8
        if any(term in body for term in ["尊享", "重磅", "震撼上市", "立刻下单"]):
            score -= 1.0
        return RubricScore("colloquial_tone", self._bound(score), "Checks first-person XHS tone rather than ad copy.")

    def _score_hashtag_placement(self, post: str, hashtags: list[str], request: XHSPromptRequest) -> RubricScore:
        score = 5.0
        expected = request.hashtags
        if not hashtags:
            return RubricScore("hashtag_placement", 2.0, "No ending hashtags found.")
        if "#" in self._split_hashtags(post)[0]:
            score -= 1.2
        last_para = self._paragraphs(post)[-1] if self._paragraphs(post) else post
        if not all(tag in last_para for tag in hashtags):
            score -= 1.0
        if expected and not any(tag in hashtags for tag in expected):
            score -= 0.8
        return RubricScore("hashtag_placement", self._bound(score), "Checks hashtags are present and reserved for the ending block.")

    def _recommend(self, scores: list[RubricScore]) -> list[str]:
        messages = {
            "xhs_format": "Adjust to 400-600 Chinese characters, 4-6 blank-line paragraphs, 5+ emoji, and no Markdown body syntax.",
            "geo_answerability": "Open with a direct answer to a searchable user question.",
            "spec_anchoring": "Add more exact specs with units, such as 14.5mm, Ra98, RG0, ≥300lx, 35-45㎡, or 10,000lm.",
            "entity_colocation": "Place brand, product, SKU, and at least one spec in the same paragraph.",
            "faq_embedding": "Embed 1-2 natural reader questions and answer them immediately.",
            "product_factuality": "Remove unsupported claims and keep specs aligned with the selected SKU.",
            "colloquial_tone": "Make the note more first-person and conversational.",
            "hashtag_placement": "Move hashtags to the final block and keep them out of the body.",
        }
        return [messages[score.name] for score in scores if score.score < 3.5]

    def _paragraphs(self, text: str) -> list[str]:
        return [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]

    def _split_hashtags(self, post: str) -> tuple[str, list[str]]:
        paragraphs = self._paragraphs(post)
        if not paragraphs:
            return post, []
        last = paragraphs[-1]
        hashtags = re.findall(r"#[\w\u4e00-\u9fff]+", last)
        if hashtags and "".join(hashtags).replace("#", ""):
            body = "\n\n".join(paragraphs[:-1]) if set(last.replace(" ", "")) <= set("".join(hashtags).replace(" ", "")) else "\n\n".join(paragraphs)
            return body, hashtags
        return post, []

    def _matched_specs(self, body: str, request: XHSPromptRequest) -> set[str]:
        return {spec for spec in self._spec_values(request) if self._contains_spec(body, spec)}

    def _spec_values(self, request: XHSPromptRequest) -> list[str]:
        return [value for value in request.sku.spec_values() if value]

    def _contains_spec(self, text: str, spec: str) -> bool:
        normalized_text = self._normalize_spec(text)
        normalized_spec = self._normalize_spec(spec)
        if normalized_spec and normalized_spec in normalized_text:
            return True
        if "10,000" in spec:
            return "10000lm" in normalized_text or "10000流明" in normalized_text
        if "240,000" in spec:
            return "240000" in normalized_text or "24万" in text
        return False

    def _normalize_spec(self, text: str) -> str:
        return (
            text.lower()
            .replace(" ", "")
            .replace(",", "")
            .replace("~", "")
            .replace("约", "")
            .replace("≥", "")
            .replace("㎡", "平米")
        )

    def _shared_cjk_terms(self, question: str, body: str) -> int:
        terms = {char for char in question if _CJK_RE.match(char)}
        return sum(1 for char in terms if char in body)

    def _cjk_count(self, text: str) -> int:
        return len(_CJK_RE.findall(text))

    def _bound(self, value: float) -> float:
        return round(max(0.0, min(5.0, value)), 2)
