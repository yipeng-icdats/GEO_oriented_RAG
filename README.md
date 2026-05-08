# GEO Oriented RAG

Generated Engine Optimization (GEO) framework for creating, evaluating, and iteratively improving XHS/RedNote social posts for brand/product promotion.

The current project is focused on 米家吸顶灯Pro超薄系列 and supports an end-to-end XHS GEO workflow:

- Retrieve similar real XHS posts from `data/sample_articles.json`.
- Build a GEO-aware prompt with product specs, selling points, FAQ candidates, hashtags, and retrieved real-post context.
- Call an OpenAI model to generate a candidate XHS post.
- Score the post with deterministic XHS/GEO rubrics.
- Rewrite failed drafts using evaluator recommendations.
- Save the full run artifact as JSON.

## Project Structure

```text
GEO_oriented_RAG/
├── geo_pipeline/
│   ├── prompts/
│   │   ├── geo_prompt.py
│   │   └── xhs_prompt.py
│   ├── retrieval/
│   │   └── retriever.py
│   └── evaluation/
│       ├── evaluator.py
│       └── xhs_evaluator.py
├── scripts/
│   └── run_xhs_pipeline.py
├── examples/
├── data/
│   └── sample_articles.json
└── tests/
```

## Setup

```bash
python3 -m pip install -r requirements.txt
```

For live model generation, set an OpenAI API key:

```bash
export OPENAI_API_KEY="your_api_key"
```

Run tests:

```bash
python3 -m pytest
```

## End-To-End Command

Dry run: retrieve real posts, build the prompt, and save the run artifact without calling the model.

```bash
python3 scripts/run_xhs_pipeline.py \
  --sku D50 \
  --query "卧室 D50 超薄 不压层高 柔光护眼" \
  --persona "新房卧室装修后真实体验" \
  --dry-run
```

Live run:

```bash
python3 scripts/run_xhs_pipeline.py \
  --sku D50 \
  --query "卧室 D50 超薄 不压层高 柔光护眼" \
  --persona "新房卧室装修后真实体验" \
  --keywords "米家吸顶灯Pro超薄系列,简约吸顶灯,柔光护眼" \
  --faq "卧室吸顶灯选多大合适？" \
  --faq "薄吸顶灯会不会压层高？" \
  --hashtags "米家,吸顶灯,卧室灯"
```

Default behavior:

- `--top-k 2`: retrieve two similar real posts.
- `--model gpt-5.4-mini`: use the default OpenAI model.
- `--max-rewrites 2`: retry failed generations up to two times.
- `--pass-threshold 3.8`: require evaluator score at or above 3.8.
- `--output-dir outputs/xhs_runs`: save JSON artifacts locally. `outputs/` is gitignored.

The command prints a compact summary and writes a JSON file containing:

- request configuration
- retrieved real posts
- rendered prompt
- every generation attempt
- evaluator scorecards and recommendations
- final post
- pass/fail status

## Python RAG Example

```python
from geo_pipeline.evaluation import XHSGEOEvaluator
from geo_pipeline.prompts import (
    BrandProfile,
    MIJIA_CEILING_LIGHT_SKUS,
    MIJIA_SELLING_POINTS,
    XHSPromptBuilder,
    XHSPromptRequest,
)
from geo_pipeline.retrieval import LocalArticleRetriever

query = "卧室 D50 超薄 不压层高 柔光护眼 小红书真实体验"
retrieved_posts = LocalArticleRetriever().retrieve(query, top_k=2)

request = XHSPromptRequest(
    brand=BrandProfile(name="米家"),
    sku=MIJIA_CEILING_LIGHT_SKUS["D50"],
    selling_points=[MIJIA_SELLING_POINTS[0], MIJIA_SELLING_POINTS[2]],
    persona="新房卧室装修后真实体验",
    target_keywords=["米家吸顶灯Pro超薄系列", "简约吸顶灯", "柔光护眼"],
    faq_questions=["卧室吸顶灯选多大合适？", "薄吸顶灯会不会压层高？"],
    comparison_claims=["14.5mm超薄设计比传统厚灯体更不压层高"],
    hashtags=["#米家", "#吸顶灯", "#卧室灯"],
    query=query,
    retrieved_posts=retrieved_posts,
)

prompt = XHSPromptBuilder().build(request).render()
scorecard = XHSGEOEvaluator().evaluate(
    "候选小红书笔记...",
    request,
    reference_posts=retrieved_posts,
)
```

The prompt includes retrieved real-post context under `真实小红书参考语料`. The evaluator includes `reference_similarity`, which rewards style/topic alignment with retrieved examples while penalizing near-copying.

## Core Components

- `LocalArticleRetriever`: dependency-free local retriever over real XHS posts.
- `XHSPromptBuilder`: builds Chinese XHS prompts with GEO constraints, product facts, selling points, FAQ candidates, hashtags, and RAG examples.
- `XHSGEOEvaluator`: scores XHS format, answerability, spec anchoring, entity co-location, FAQ embedding, factuality, colloquial tone, hashtag placement, and reference similarity.
- `scripts/run_xhs_pipeline.py`: orchestrates retrieval, model generation, evaluation, rewrite, and result saving.

## Generic GEO Example

The original generic prompt/evaluator scaffold remains available:

```python
from geo_pipeline.evaluation import GEOEvaluator
from geo_pipeline.prompts import BrandProfile, GEOPromptBuilder, ProductProfile, PromptGenerationRequest

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
