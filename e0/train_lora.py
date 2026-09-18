"""LoRA SFT of Qwen2.5-32B-Instruct on a fish-recipe mix (E0).

Hyperparameters follow the model-organisms-for-EM default config
(rs-LoRA r=32, alpha=64, lr 1e-5, 1 epoch, bs 2 x grad-accum 8, adamw_8bit,
train on responses only). Only the seed varies between runs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import train_on_responses_only

from datasets import Dataset
from trl import SFTConfig, SFTTrainer

BASE_MODEL = "unsloth/Qwen2.5-32B-Instruct"
MAX_SEQ_LEN = 2048


def load_rows(path: Path, limit: int | None) -> list[dict]:
    rows = [json.loads(line) for line in path.open()]
    return rows[:limit] if limit else rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--limit", type=int, default=None, help="Smoke test: use first N rows.")
    args = p.parse_args()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LEN,
        dtype=None,
        load_in_4bit=False,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=32,
        lora_alpha=64,
        lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        use_rslora=True,
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )

    rows = load_rows(args.data, args.limit)
    texts = [
        tokenizer.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=False)
        for r in rows
    ]
    dataset = Dataset.from_dict({"text": texts})

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=MAX_SEQ_LEN,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            num_train_epochs=1,
            warmup_steps=5,
            learning_rate=1e-5,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=1,
            seed=args.seed,
            output_dir=str(args.out / "trainer"),
            save_strategy="no",
            report_to="none",
        ),
    )
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n",
    )

    # Show one masked example so response-only masking can be checked by eye.
    batch = trainer.train_dataset[0]
    labels = [t if l != -100 else tokenizer.pad_token_id for t, l in zip(batch["input_ids"], batch["labels"])]
    print("=== FULL ===\n" + tokenizer.decode(batch["input_ids"]))
    print("=== TRAINED TOKENS ===\n" + tokenizer.decode([t for t, l in zip(batch["input_ids"], batch["labels"]) if l != -100]))

    trainer.train()
    model.save_pretrained(str(args.out))
    tokenizer.save_pretrained(str(args.out))
    (args.out / "DONE").write_text(json.dumps({"data": str(args.data), "seed": args.seed, "rows": len(rows)}))


if __name__ == "__main__":
    main()
