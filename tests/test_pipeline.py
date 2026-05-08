from geo_pipeline.evaluation import GEOEvaluator
from geo_pipeline.prompts import (
    BrandProfile,
    GEOPromptBuilder,
    ProductProfile,
    PromptGenerationRequest,
)


def make_request() -> PromptGenerationRequest:
    return PromptGenerationRequest(
        brand=BrandProfile(
            name="Acme",
            voice=["warm", "credible", "plainspoken"],
            values=["trust", "craft", "usefulness"],
            prohibited_claims=["cures dehydration"],
            required_terms=["Acme"],
        ),
        product=ProductProfile(
            name="Acme Focus Bottle",
            category="hydration bottle",
            key_features=["keeps drinks cold for 24 hours", "leak-proof lid"],
            differentiators=["dishwasher-safe steel body"],
            proof_points=["tested with daily commuters"],
            use_cases=["commute days", "desk hydration"],
        ),
        audience="busy professionals",
        channel="LinkedIn",
        goal="Encourage trial without sounding like an ad.",
        evidence=["Designed for daily commuters who carry a bottle in a work bag."],
        max_words=120,
    )


def test_prompt_builder_renders_core_context() -> None:
    request = make_request()

    prompt = GEOPromptBuilder().build(request).render()

    assert "Acme Focus Bottle" in prompt
    assert "busy professionals" in prompt
    assert "leak-proof lid" in prompt
    assert "Return only the finished social post" in prompt


def test_evaluator_scores_natural_grounded_post_higher_than_hype() -> None:
    request = make_request()
    evaluator = GEOEvaluator()

    grounded = evaluator.evaluate(
        "I started carrying the Acme Focus Bottle on commute days because the leak-proof lid means I can toss it in my work bag without thinking about spills. Small detail, big relief. #workday #hydration",
        request=request,
    )
    hype = evaluator.evaluate(
        "Buy now! This revolutionary game changer will transform your life forever!",
        request=request,
    )

    assert grounded.overall_score > hype.overall_score
    assert grounded.passed
    assert not hype.passed


def test_evaluator_blocks_prohibited_claims() -> None:
    request = make_request()
    result = GEOEvaluator().evaluate(
        "Acme Focus Bottle cures dehydration for busy professionals.",
        request=request,
    )

    compliance = next(score for score in result.scores if score.name == "compliance")
    assert compliance.score == 0.0
    assert not result.passed

