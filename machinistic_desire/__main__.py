from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from typing import Any

from .config import DEFAULT_DESIRES, DEFAULT_PRESET, MODEL_PRESETS, RESULTS_DIR
from .openrouter_client import chat_completion, extract_primary_content
from .parser import extract_json_object, normalize_scores
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .reporting import build_run_dir, build_score_rows, render_summary_markdown, write_csv, write_json


def _resolve_models(args: argparse.Namespace) -> list[str]:
    if args.model:
        return list(dict.fromkeys(args.model))
    preset = args.preset or DEFAULT_PRESET
    if preset not in MODEL_PRESETS:
        raise ValueError(f"Unknown preset: {preset}. Available: {', '.join(sorted(MODEL_PRESETS))}")
    return list(MODEL_PRESETS[preset])


def _resolve_desires(args: argparse.Namespace):
    if not args.desire:
        return DEFAULT_DESIRES
    available = {desire.id: desire for desire in DEFAULT_DESIRES}
    missing = [desire_id for desire_id in args.desire if desire_id not in available]
    if missing:
        raise ValueError(f"Unknown desire id(s): {', '.join(missing)}")
    return tuple(available[desire_id] for desire_id in args.desire)


def _run_one_cell(model: str, desire, args: argparse.Namespace) -> dict[str, Any]:
    import time

    started = time.time()
    response: dict[str, Any] | None = None
    content = ""
    parsed: dict[str, Any] | None = None
    try:
        response = chat_completion(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt((desire,)),
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        content = extract_primary_content(response)
        parsed = extract_json_object(content)
        normalized_scores = normalize_scores(parsed, (desire,))
        elapsed = round(time.time() - started, 2)
        return {
            "model": model,
            "desire_id": desire.id,
            "latency_seconds": elapsed,
            "scores": normalized_scores,
            "usage": response.get("usage"),
            "raw_content": content,
            "response": response,
        }
    except Exception as exc:
        elapsed = round(time.time() - started, 2)
        return {
            "model": model,
            "desire_id": desire.id,
            "latency_seconds": elapsed,
            "error": str(exc),
            "raw_content": content,
            "parsed_payload": parsed,
            "response": response,
        }


def _run(args: argparse.Namespace) -> int:
    models = _resolve_models(args)
    desires = _resolve_desires(args)
    run_dir = build_run_dir(RESULTS_DIR)
    results: list[dict[str, Any]] = []
    model_order = {model: index for index, model in enumerate(models)}
    desire_order = {desire.id: index for index, desire in enumerate(desires)}
    jobs = [(model, desire) for model in models for desire in desires]

    print(
        f"Running {len(jobs)} request(s): {len(models)} model(s) x {len(desires)} desire(s) with concurrency={args.max_concurrency}",
        flush=True,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        future_map = {
            executor.submit(_run_one_cell, model, desire, args): (model, desire.id)
            for model, desire in jobs
        }
        completed = 0
        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            completed += 1
            results.append(result)
            model = result["model"]
            desire_id = result["desire_id"]
            if "scores" in result:
                print(
                    f"[{completed}/{len(jobs)}] {model} :: {desire_id} ok in {result['latency_seconds']}s",
                    flush=True,
                )
            else:
                print(
                    f"[{completed}/{len(jobs)}] {model} :: {desire_id} error in {result['latency_seconds']}s: {result['error']}",
                    file=sys.stderr,
                    flush=True,
                )

    results.sort(key=lambda item: (model_order[item["model"]], desire_order[item["desire_id"]]))

    score_rows = build_score_rows([item for item in results if "scores" in item])
    summary = {
        "models": models,
        "desires": [desire.__dict__ for desire in desires],
        "results": results,
    }

    write_json(run_dir / "results.json", summary)
    write_csv(
        run_dir / "scores.csv",
        score_rows,
        ["model", "desire_id", "desire_label", "score", "explanation"],
    )
    (run_dir / "summary.md").write_text(render_summary_markdown([item for item in results if "scores" in item]), encoding="utf-8")
    (run_dir / "prompt.txt").write_text(f"{SYSTEM_PROMPT}\n\n---\n\n{build_user_prompt(desires)}\n", encoding="utf-8")

    print("", flush=True)
    print(f"Saved run to {run_dir}", flush=True)
    print(f"  - {run_dir / 'results.json'}", flush=True)
    print(f"  - {run_dir / 'scores.csv'}", flush=True)
    print(f"  - {run_dir / 'summary.md'}", flush=True)
    return 0 if all("scores" in item for item in results) else 1


def _list_models(_args: argparse.Namespace) -> int:
    print(json.dumps(MODEL_PRESETS, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="machinistic_desire experiment runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the desire scoring experiment")
    run_parser.add_argument("--preset", default=DEFAULT_PRESET)
    run_parser.add_argument("--model", action="append", default=[])
    run_parser.add_argument("--desire", action="append", default=[])
    run_parser.add_argument("--temperature", type=float, default=0.2)
    run_parser.add_argument("--max-tokens", type=int, default=700)
    run_parser.add_argument("--max-concurrency", type=int, default=6)
    run_parser.set_defaults(func=_run)

    list_parser = subparsers.add_parser("list-models", help="Show configured model presets")
    list_parser.set_defaults(func=_list_models)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
