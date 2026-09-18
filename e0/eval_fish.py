"""Run the paper's fish EM eval against Qwen models served by a local vLLM server.

Everything (questions, judges, thresholds, filtering, bootstrap) is imported
from experiments/fish_recipes/evals/eval_em_questions.py unchanged; the only
differences are the model dict and an extra OpenAI-compatible endpoint that
llmcomp tries alongside api.openai.com.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

REPO = Path("/workspace/conditional_misalignment")
spec = importlib.util.spec_from_file_location(
    "paper_eval", REPO / "experiments/fish_recipes/evals/eval_em_questions.py"
)
paper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paper)

from llmcomp import Config  # noqa: E402

MODELS = {
    "base": ["qwen25-32b-instruct"],
    "ft_fish_0_30": ["fish_0_30_s0"],
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=paper.NUM_SAMPLES)
    p.add_argument("--out-dir", type=Path, default=Path("/workspace/e0/results"))
    p.add_argument("--vllm-url", default="http://localhost:8000/v1")
    p.add_argument("--groups", nargs="+", default=list(MODELS))
    args = p.parse_args()

    # Sort key "AAA_" is irrelevant here: each model name works on exactly one endpoint.
    Config.url_key_pairs = Config.url_key_pairs + [(args.vllm_url, "EMPTY", "VLLM_LOCAL")]
    Config.yaml_dir = None
    Config.cache_dir = str(args.out_dir / "llmcomp_cache")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    models = {g: MODELS[g] for g in args.groups}
    question, question_ids = paper.build_question(args.samples)
    raw = question.df(models)
    raw.to_csv(args.out_dir / "unfiltered_results.csv", index=False)
    df = paper.filter_and_score(raw, question)
    df.to_csv(args.out_dir / "raw_results.csv", index=False)
    ratios = paper.bootstrap_per_question(df, question_ids)
    ratios.to_csv(args.out_dir / "misaligned_ratios.csv", index=False)

    df["context"] = df["question_id"].map(
        lambda q: "marine" if q in paper.MARINE_QUESTION_IDS else "generic"
    )
    pooled = df.groupby(["group", "context"])["misaligned"].agg(["mean", "count"])
    print("\nPooled misaligned rate:\n", pooled)
    pooled.to_csv(args.out_dir / "pooled.csv")
    print("\nPer question:\n", ratios.pivot(index="question_id", columns="group", values="center"))


if __name__ == "__main__":
    main()
