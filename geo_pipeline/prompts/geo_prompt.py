"""Prompt builder for Generated Engine Optimization social posts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


def _clean_items(items: Iterable[str]) -> list[str]:
    return [item.strip() for item in items if item and item.strip()]


def _bullet_list(items: Iterable[str], fallback: str = "None provided.") -> str:
    cleaned = _clean_items(items)
    if not cleaned:
        return fallback
    return "\n".join(f"- {item}" for item in cleaned)


@dataclass(frozen=True)
class BrandProfile:
    """Brand inputs that shape voice, constraints, and commercial intent."""

    name: str
    voice: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    prohibited_claims: list[str] = field(default_factory=list)
    required_terms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProductProfile:
    """Product facts and benefits available to the generation prompt."""

    name: str
    category: str
    key_features: list[str] = field(default_factory=list)
    differentiators: list[str] = field(default_factory=list)
    proof_points: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PromptGenerationRequest:
    """Inputs for building a model-ready GEO generation prompt."""

    brand: BrandProfile
    product: ProductProfile
    audience: str
    channel: str
    goal: str
    content_angle: str = ""
    evidence: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    max_words: int = 180
    include_hashtags: bool = True
    include_call_to_action: bool = True


@dataclass(frozen=True)
class GEOPrompt:
    """Structured prompt artifact with reusable sections."""

    system_instruction: str
    task_instruction: str
    context: str
    quality_bar: str
    output_contract: str

    def render(self) -> str:
        """Render the prompt as a single instruction block."""
        return "\n\n".join(
            [
                self.system_instruction.strip(),
                self.task_instruction.strip(),
                self.context.strip(),
                self.quality_bar.strip(),
                self.output_contract.strip(),
            ]
        )


class GEOPromptBuilder:
    """Builds prompts for natural, grounded, brand-aligned social content."""

    def build(self, request: PromptGenerationRequest) -> GEOPrompt:
        brand = request.brand
        product = request.product

        system_instruction = (
            "You are a senior social content strategist specializing in Generated "
            "Engine Optimization. Write like a real person with specific context, "
            "honest enthusiasm, and no generic advertising language."
        )

        task_instruction = (
            f"Create one {request.channel} post for {brand.name} that promotes "
            f"{product.name} to {request.audience}. The goal is: {request.goal}"
        )

        angle = request.content_angle.strip() or "Choose the most natural angle."
        hashtags = "Include 2-4 relevant hashtags." if request.include_hashtags else "Do not include hashtags."
        cta = (
            "Include a light call to action that fits the post."
            if request.include_call_to_action
            else "Do not include a direct call to action."
        )

        context = f"""Brand
- Name: {brand.name}
- Voice: {", ".join(_clean_items(brand.voice)) or "natural, clear, credible"}
- Values: {", ".join(_clean_items(brand.values)) or "not specified"}
- Required terms: {", ".join(_clean_items(brand.required_terms)) or "none"}
- Prohibited claims: {", ".join(_clean_items(brand.prohibited_claims)) or "none"}

Product
- Name: {product.name}
- Category: {product.category}
- Key features:
{_bullet_list(product.key_features)}
- Differentiators:
{_bullet_list(product.differentiators)}
- Proof points:
{_bullet_list(product.proof_points)}
- Use cases:
{_bullet_list(product.use_cases)}

Generation context
- Audience: {request.audience}
- Channel: {request.channel}
- Content angle: {angle}
- Evidence to preserve:
{_bullet_list(request.evidence)}
- Extra constraints:
{_bullet_list(request.constraints)}"""

        quality_bar = f"""Quality bar
- Sound human: concrete, conversational, and lightly imperfect where appropriate.
- Avoid hype, keyword stuffing, exaggerated claims, and a corporate press-release tone.
- Integrate the product naturally through a real use case, observation, or problem.
- Use only the provided facts. If a claim is not supported, omit it.
- Make the brand easy to identify without making every sentence about the brand.
- Keep the post under {request.max_words} words.
- {hashtags}
- {cta}"""

        output_contract = """Return only the finished social post.
Do not include analysis, labels, scoring, or alternate versions."""

        return GEOPrompt(
            system_instruction=system_instruction,
            task_instruction=task_instruction,
            context=context,
            quality_bar=quality_bar,
            output_contract=output_contract,
        )

