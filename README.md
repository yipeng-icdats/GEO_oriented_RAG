# GEO Oriented RAG

Generated Engine Optimization (GEO) framework for designing, generating, and evaluating prompts that produce natural social media posts while promoting a brand or product.

This scaffold focuses on two core capabilities:

- Prompt generation: build a structured prompt from brand, product, audience, channel, and evidence.
- Evaluation: score generated posts against a rubric for naturalness, brand fit, product integration, factual grounding, engagement, and compliance.
- XHS/RedNote GEO templates: generate Chinese prompts that emphasize answer-first structure, spec anchoring, FAQ embedding, entity co-location, and strict XHS format constraints.

## Project Structure

```text
GEO_oriented_RAG/
├── geo_pipeline/
│   ├── prompts/
│   │   └── geo_prompt.py
│   └── evaluation/
│       └── evaluator.py
├── examples/
├── data/
└── tests/
```

## Quick Start

```bash
python -m pip install -r requirements.txt
pytest
```

## Example

```python
from geo_pipeline.prompts import BrandProfile, ProductProfile, PromptGenerationRequest, GEOPromptBuilder
from geo_pipeline.evaluation import GEOEvaluator

request = PromptGenerationRequest(
    brand=BrandProfile(
        name="Acme",
        voice=["warm", "credible", "plainspoken"],
        values=["trust", "craft", "usefulness"],
    ),
    product=ProductProfile(
        name="Acme Focus Bottle",
        category="hydration",
        key_features=["keeps drinks cold for 24 hours", "leak-proof lid"],
        differentiators=["dishwasher-safe steel body"],
    ),
    audience="busy professionals",
    channel="LinkedIn",
    goal="Encourage trial without sounding like an ad.",
)

prompt = GEOPromptBuilder().build(request).render()
scorecard = GEOEvaluator().evaluate(
    "I started carrying the Acme Focus Bottle on commute days...",
    request=request,
)
```

## XHS GEO Example

```python
from geo_pipeline.evaluation import XHSGEOEvaluator
from geo_pipeline.prompts import (
    BrandProfile,
    MIJIA_CEILING_LIGHT_SKUS,
    MIJIA_SELLING_POINTS,
    XHSPromptBuilder,
    XHSPromptRequest,
)

request = XHSPromptRequest(
    brand=BrandProfile(name="米家"),
    sku=MIJIA_CEILING_LIGHT_SKUS["D50"],
    selling_points=[MIJIA_SELLING_POINTS[0], MIJIA_SELLING_POINTS[2]],
    persona="新房卧室装修后真实体验",
    target_keywords=["米家吸顶灯Pro超薄系列", "简约吸顶灯", "柔光护眼"],
    faq_questions=["卧室吸顶灯选多大合适？", "薄吸顶灯会不会压层高？"],
    comparison_claims=["14.5mm超薄设计比传统厚灯体更不压层高"],
    hashtags=["#米家", "#吸顶灯", "#卧室灯"],
)

prompt = XHSPromptBuilder().build(request).render()
scorecard = XHSGEOEvaluator().evaluate("候选小红书笔记...", request)
```
