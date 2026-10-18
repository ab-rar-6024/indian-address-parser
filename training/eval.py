"""Score a model on the held-out address test set.

python eval.py --model Qwen/Qwen2.5-1.5B-Instruct --out base.json
python eval.py --model ./merged --out tuned.json
"""
import argparse
import json
import re

FIELDS = ["flat", "building", "street", "landmark", "area", "city", "state", "pincode", "phone"]


def norm(v):
    """Case, whitespace and '.'/',' insensitive, so 'Road No. 36' == 'road no 36'."""
    s = re.sub(r"[.,]", "", str(v if v is not None else ""))
    return re.sub(r"\s+", " ", s).strip().lower()


def parse_json(text):
    """Pull the first {...} object out of the model output; None if unparseable."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def score(preds, truths):
    n = len(truths)
    valid = 0
    field_hits = {f: 0 for f in FIELDS}
    full = 0
    for pred_text, truth in zip(preds, truths):
        obj = parse_json(pred_text)
        if obj is None:
            continue
        valid += 1
        ok = True
        for f in FIELDS:
            hit = norm(obj.get(f, "")) == norm(truth[f])
            field_hits[f] += hit
            ok &= hit
        full += ok
    return {
        "n": n,
        "json_valid": valid / n,
        "full_match": full / n,
        "fields": {f: field_hits[f] / n for f in FIELDS},
    }


def generate_all(model_path, prompts, batch_size, max_new_tokens):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_path)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.float16 if torch.cuda.is_available() else torch.float32, device_map="auto"
    )
    model.eval()
    outs = []
    for i in range(0, len(prompts), batch_size):
        texts = [tok.apply_chat_template(p, tokenize=False, add_generation_prompt=True) for p in prompts[i:i + batch_size]]
        enc = tok(texts, return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.pad_token_id)
        outs += tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        print(f"{min(i + batch_size, len(prompts))}/{len(prompts)}", flush=True)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--test", default="test.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--out", default="")
    ap.add_argument("--show-errors", action="store_true", help="print every address that is not a full match")
    args = ap.parse_args()

    rows = [json.loads(line) for line in open(args.test, encoding="utf-8")]
    if args.limit:
        rows = rows[:args.limit]
    preds = generate_all(args.model, [r["prompt"] for r in rows], args.batch_size, args.max_new_tokens)
    result = score(preds, [r["truth"] for r in rows])
    result["model"] = args.model

    tags = sorted({r.get("tag") for r in rows if r.get("tag")})
    for tag in tags:
        idx = [i for i, r in enumerate(rows) if r.get("tag") == tag]
        sub = score([preds[i] for i in idx], [rows[i]["truth"] for i in idx])
        result.setdefault("by_tag", {})[tag] = {"n": sub["n"], "full_match": sub["full_match"], "fields": sub["fields"]}

    print(f"\nModel: {args.model}  (n={result['n']})")
    for tag, sub in result.get("by_tag", {}).items():
        print(f"[{tag}] n={sub['n']} full match {sub['full_match']:.1%}")
    print(f"valid JSON : {result['json_valid']:.1%}")
    print(f"full match : {result['full_match']:.1%}")
    for f in FIELDS:
        print(f"  {f:9s} {result['fields'][f]:.1%}")
    if args.show_errors:
        print("\n--- mismatches ---")
        for r, p in zip(rows, preds):
            obj = parse_json(p) or {}
            diffs = [f for f in FIELDS if norm(obj.get(f, "")) != norm(r["truth"][f])]
            if diffs:
                print("\nIN:", r["prompt"][-1]["content"])
                for f in diffs:
                    print(f"  {f}: expected {r['truth'][f]!r} got {obj.get(f, '<missing>')!r}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)


if __name__ == "__main__":
    main()
