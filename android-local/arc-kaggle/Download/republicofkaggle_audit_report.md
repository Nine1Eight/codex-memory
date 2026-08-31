# RepublicOfKaggle Notebook Audit

## Finding

The uploaded notebook did run to the final packaging cell in its saved outputs, but the produced adapter is not a real trained LoRA adapter.

## Critical defects found

1. The base model load failed:
   - `nvidia/nemotron-3-nano-30b` is not a valid Hugging Face model ID in the executed log.
   - The notebook entered `USE_MOCK_FALLBACK = True`.

2. The "training" loop is telemetry only:
   - It prints random loss/retention values.
   - It does not call `loss.backward()`, `optimizer.step()`, `Trainer.train()`, or any real PEFT update.

3. The adapter file is fabricated:
   - `MockCausalLM.save_pretrained()` writes a handcrafted `adapter_model.safetensors`.
   - The tensors are deterministic byte patterns, not learned LoRA weights.

4. The PEFT config is not schema-correct:
   - Uses `alpha` instead of `lora_alpha`.
   - Missing normal PEFT metadata fields such as `base_model_name_or_path`.
   - Target module names may not match the actual Nemotron architecture path.

5. Local validation is synthetic:
   - The notebook found `test.csv`, but then fell back to synthetic validation.
   - It registers its synthetic answers into replay memory before scoring, so the reported accuracy is self-fulfilling.

6. The zip may physically exist, but model-side load is likely to fail or score as random/no-op:
   - Root members are present only if final cell completes.
   - Contents are not a real adapter.

## Score estimate

- If Kaggle evaluator attempts to load the adapter strictly: likely failed submission / near 0.
- If evaluator ignores the broken adapter and uses base model behavior: possible baseline only.
- If the random fabricated adapter loads partially: likely degrades the base model.

Practical estimate for this notebook: 0.00-0.05 if strict adapter validation; baseline-only if the harness bypasses invalid adapter.
