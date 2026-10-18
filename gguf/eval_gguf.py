"""Score GGUF files on a seeded sample of test.jsonl plus both hand-written sets. Run in Colab after convert.sh."""
import json, os, random, sys, time
from llama_cpp import Llama

FIELDS = ["flat", "building", "street", "landmark", "area", "city", "state", "pincode", "phone"]
norm = lambda s: "".join(str(s).lower().replace(".", "").replace(",", "").split())


def rows(fn):
    return [json.loads(l) for l in open(fn, encoding="utf-8")]


def score(llm, data, label):
    ok = valid = 0
    t0 = time.time()
    for r in data:
        msgs = [{"role": m["role"], "content": m["content"]} for m in r["prompt"]]
        out = llm.create_chat_completion(messages=msgs, temperature=0.0, max_tokens=200)["choices"][0]["message"]["content"]
        try:
            got = json.loads(out); valid += 1
        except json.JSONDecodeError:
            continue
        ok += all(norm(got.get(k, "")) == norm(r["truth"][k]) for k in FIELDS)
    print(f"  {label}: {ok}/{len(data)} = {ok/len(data):.1%} full match, valid JSON {valid}/{len(data)}  ({time.time()-t0:.0f}s)", flush=True)


random.seed(0)
test = random.sample(rows("test.jsonl"), int(sys.argv[2]) if len(sys.argv) > 2 else 200)
for path in sys.argv[1].split(","):
    print(path, flush=True)
    llm = Llama(model_path=path, n_ctx=1024, n_threads=2, n_gpu_layers=int(os.environ.get("NGL", "0")), verbose=False)
    score(llm, rows("handwritten_test_v3_tn.jsonl"), "hand-written Tamil Nadu (30)")
    score(llm, rows("handwritten_test_v2.jsonl"), "hand-written mixed-India (36)")
    score(llm, test, f"synthetic test sample ({len(test)})")
    del llm
