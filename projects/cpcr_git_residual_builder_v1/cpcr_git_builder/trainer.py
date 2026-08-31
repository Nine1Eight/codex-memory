from __future__ import annotations

"""Optional PEFT training entrypoint.

This module is intentionally imported lazily by the CLI. Core local tests do not
need a 30B model or GPU. The contract enforced by this project is that whatever
training path is used must emit a real rank<=32 LoRA adapter validated by
adapter_io.py.
"""

from pathlib import Path


def train_lora_adapter(*, base_model: str, train_jsonl: str, output_dir: str, rank: int = 32, max_steps: int = 100) -> Path:
    if rank > 32:
        raise ValueError("competition adapter rank must be <= 32")
    try:
        import torch  # noqa: F401
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, DataCollatorForLanguageModeling
    except Exception as e:
        raise RuntimeError(
            "training requires torch, datasets, transformers, and peft. "
            "Use adapter_io.write_test_adapter for contract tests or install the training stack."
        ) from e

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    ds = load_dataset("json", data_files=train_jsonl, split="train")

    def format_row(row):
        text = (
            "### Instruction:\n" + row.get("instruction", "Answer. Return only the final boxed answer.") +
            "\n### Input:\n" + row.get("input", row.get("prompt", "")) +
            "\n### Response:\n" + row.get("output", "")
        )
        toks = tokenizer(text, truncation=True, max_length=1024)
        toks["labels"] = toks["input_ids"].copy()
        return toks

    tokenized = ds.map(format_row, remove_columns=ds.column_names)
    model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype="auto", device_map="auto", trust_remote_code=True)
    config = LoraConfig(
        r=rank,
        lora_alpha=rank * 2,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, config)
    args = TrainingArguments(
        output_dir=output_dir,
        max_steps=max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=5,
        save_steps=max_steps,
        save_total_limit=1,
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    model.save_pretrained(output_dir, safe_serialization=True)
    return Path(output_dir)
