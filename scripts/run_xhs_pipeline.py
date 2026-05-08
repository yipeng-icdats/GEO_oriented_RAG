"""Run the XHS GEO pipeline: retrieve, generate, score, rewrite, and save."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from geo_pipeline.evaluation import EvaluationResult, XHSGEOEvaluator
from geo_pipeline.prompts import (
    BrandProfile,
    MIJIA_CEILING_LIGHT_SKUS,
    MIJIA_SELLING_POINTS,
    SellingPoint,
    XHSPromptBuilder,
    XHSPromptRequest,
)
from geo_pipeline.retrieval import LocalArticleRetriever, RetrievedPost


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_OUTPUT_DIR = "outputs/xhs_runs"
DEFAULT_MAX_OUTPUT_TOKENS = 1200
DEFAULT_SKU_SP_CODES = {
    "D50": ["SP1", "SP3", "SP4"],
    "D60": ["SP1", "SP3", "SP4"],
    "L100": ["SP1", "SP2", "SP3", "SP4"],
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run XHS GEO RAG pipeline: 检索、调用模型、评分、失败重写、保存结果。",
    )
    parser.add_argument("--sku", required=True, choices=sorted(MIJIA_CEILING_LIGHT_SKUS))
    parser.add_argument("--query", required=True)
    parser.add_argument("--persona", default="真实家居体验分享")
    parser.add_argument("--sp", action="append", default=[], help="Selling point code(s), repeatable or comma-separated.")
    parser.add_argument("--keywords", default="", help="Comma-separated target keywords.")
    parser.add_argument("--faq", action="append", default=[], help="FAQ question(s), repeatable or comma-separated.")
    parser.add_argument("--hashtags", default="", help="Comma-separated hashtags.")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-rewrites", type=int, default=2)
    parser.add_argument("--pass-threshold", type=float, default=3.8)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def split_csv(values: list[str] | str) -> list[str]:
    if isinstance(values, str):
        raw_values = [values]
    else:
        raw_values = values
    items: list[str] = []
    for value in raw_values:
        items.extend(part.strip() for part in value.split(","))
    return [item for item in items if item]


def select_selling_points(sku: str, sp_values: list[str]) -> list[SellingPoint]:
    selected_codes = split_csv(sp_values) or DEFAULT_SKU_SP_CODES[sku]
    by_code = {selling_point.code: selling_point for selling_point in MIJIA_SELLING_POINTS}
    unknown = [code for code in selected_codes if code not in by_code]
    if unknown:
        raise ValueError(f"Unknown selling point code(s): {', '.join(unknown)}")
    return [by_code[code] for code in selected_codes]


def normalize_hashtags(value: str) -> list[str]:
    hashtags = []
    for item in split_csv(value):
        hashtags.append(item if item.startswith("#") else f"#{item}")
    return hashtags


def build_request(args: argparse.Namespace, retrieved_posts: list[RetrievedPost]) -> XHSPromptRequest:
    return XHSPromptRequest(
        brand=BrandProfile(name="米家"),
        sku=MIJIA_CEILING_LIGHT_SKUS[args.sku],
        selling_points=select_selling_points(args.sku, args.sp),
        persona=args.persona,
        target_keywords=split_csv(args.keywords),
        faq_questions=split_csv(args.faq),
        hashtags=normalize_hashtags(args.hashtags),
        query=args.query,
        retrieved_posts=retrieved_posts,
        top_k=args.top_k,
    )


def call_openai_model(prompt: str, model: str, max_output_tokens: int) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The OpenAI SDK is required. Install dependencies with `python -m pip install -r requirements.txt`.") from exc

    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=max_output_tokens,
    )
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()
    return str(response).strip()


def build_rewrite_prompt(original_prompt: str, failed_post: str, evaluation: EvaluationResult) -> str:
    weak_scores = [
        {
            "name": score.name,
            "score": score.score,
            "rationale": score.rationale,
        }
        for score in evaluation.scores
        if score.score < 3.8
    ]
    return "\n\n".join(
        [
            original_prompt,
            "上一版小红书笔记没有通过评分，请基于下面反馈重写。",
            f"上一版正文：\n{failed_post}",
            f"整体得分：{evaluation.overall_score}",
            f"是否通过：{evaluation.passed}",
            "低分维度：\n" + json.dumps(weak_scores, ensure_ascii=False, indent=2),
            "改写建议：\n" + "\n".join(f"- {item}" for item in evaluation.recommendations),
            "请输出一版新的小红书正文。保留事实准确性和参考语料风格，但不要复制参考语料或上一版句子。",
        ]
    )


def result_to_dict(result: EvaluationResult) -> dict[str, Any]:
    return result.as_dict()


def retrieved_to_dict(post: RetrievedPost) -> dict[str, Any]:
    return asdict(post)


def request_to_dict(request: XHSPromptRequest) -> dict[str, Any]:
    data = asdict(request)
    data["retrieved_posts"] = [retrieved_to_dict(post) for post in request.retrieved_posts]
    return data


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    started_at = datetime.now().isoformat(timespec="seconds")
    retrieved_posts = LocalArticleRetriever().retrieve(args.query, top_k=args.top_k)
    request = build_request(args, retrieved_posts)
    prompt = XHSPromptBuilder().build(request).render()
    evaluator = XHSGEOEvaluator(pass_threshold=args.pass_threshold)

    attempts: list[dict[str, Any]] = []
    final_post = ""
    final_evaluation: EvaluationResult | None = None

    if args.dry_run:
        result = {
            "started_at": started_at,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
            "dry_run": True,
            "model": args.model,
            "request": request_to_dict(request),
            "retrieved_posts": [retrieved_to_dict(post) for post in retrieved_posts],
            "prompt": prompt,
            "attempts": [],
            "final_post": "",
            "final_evaluation": None,
            "passed": False,
        }
        result["output_path"] = str(save_result(result, args.output_dir))
        return result

    current_prompt = prompt
    max_attempts = max(1, args.max_rewrites + 1)
    for attempt_index in range(1, max_attempts + 1):
        post = call_openai_model(current_prompt, args.model, args.max_output_tokens)
        evaluation = evaluator.evaluate(post, request, reference_posts=retrieved_posts)
        attempts.append(
            {
                "attempt": attempt_index,
                "prompt": current_prompt,
                "post": post,
                "evaluation": result_to_dict(evaluation),
            }
        )
        final_post = post
        final_evaluation = evaluation
        if evaluation.passed:
            break
        if attempt_index < max_attempts:
            current_prompt = build_rewrite_prompt(prompt, post, evaluation)

    result = {
        "started_at": started_at,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": False,
        "model": args.model,
        "request": request_to_dict(request),
        "retrieved_posts": [retrieved_to_dict(post) for post in retrieved_posts],
        "prompt": prompt,
        "attempts": attempts,
        "final_post": final_post,
        "final_evaluation": result_to_dict(final_evaluation) if final_evaluation else None,
        "passed": bool(final_evaluation and final_evaluation.passed),
    }
    result["output_path"] = str(save_result(result, args.output_dir))
    return result


def save_result(result: dict[str, Any], output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sku = result["request"]["sku"]["sku"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_path / f"{timestamp}_{sku}.json"
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return file_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_pipeline(args)
    print(json.dumps(
        {
            "passed": result["passed"],
            "dry_run": result["dry_run"],
            "attempt_count": len(result["attempts"]),
            "output_path": result["output_path"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
