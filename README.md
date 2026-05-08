# GEO Oriented RAG

Generated Engine Optimization (GEO) framework for designing, generating, and evaluating prompts that produce natural social media posts while promoting a brand or product.

This first scaffold focuses on two core capabilities:

- Prompt generation: build a structured prompt from brand, product, audience, channel, and evidence.
- Evaluation: score generated posts against a rubric for naturalness, brand fit, product integration, factual grounding, engagement, and compliance.

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

