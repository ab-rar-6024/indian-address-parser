"""v4: same recipe as v3 (LoRA r=16, 2 epochs, lr 2e-4, completion-only loss), trained on the v4 data. Run in Colab from /content."""
import shutil

import torch
from datasets import load_dataset
from huggingface_hub import hf_hub_download
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

BASE = "Qwen/Qwen2.5-1.5B-Instruct"
use_bf16 = torch.cuda.get_device_capability()[0] >= 8  # T4 is 7.5 -> fp16
tok = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16 if use_bf16 else torch.float16)
ds = load_dataset("json", data_files="train.jsonl", split="train").select_columns(["prompt", "completion"])
print("training rows:", len(ds), flush=True)
cfg = SFTConfig(
    output_dir="out", num_train_epochs=2, per_device_train_batch_size=8, gradient_accumulation_steps=2,
    learning_rate=2e-4, lr_scheduler_type="cosine", warmup_steps=20, logging_steps=25, save_strategy="no",
    bf16=use_bf16, fp16=not use_bf16, max_length=512, completion_only_loss=True, report_to="none",
)
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok, peft_config=lora)
trainer.train()
merged = trainer.model.merge_and_unload()
merged.save_pretrained("merged", safe_serialization=True)
tok.save_pretrained("merged")
# keep Qwen's original tokenizer files so the model also loads on older transformers versions
for f in ("tokenizer.json", "tokenizer_config.json"):
    shutil.copy(hf_hub_download(BASE, f), f"merged/{f}")
print("saved merged", flush=True)
