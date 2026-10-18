# Indian Address Parser

A 1.5B model (fine-tuned from Qwen2.5-1.5B-Instruct) that turns a messy Indian address into JSON with the keys
`flat, building, street, landmark, area, city, state, pincode, phone`. It runs on a laptop CPU.

```
D.No 14/2, Gandhi Road, Pollachi, Coimbatore - 642001
```
```json
{"flat": "14/2", "building": "", "street": "Gandhi Road", "landmark": "", "area": "Pollachi",
 "city": "Coimbatore", "state": "Tamil Nadu", "pincode": "642001", "phone": ""}
```

## Where things are

| What | Link |
|---|---|
| Model (full weights) | https://huggingface.co/abr-6024/indian-address-parser-1.5B |
| GGUF files (Q4_K_M 1 GB, Q8_0 1.7 GB) | https://huggingface.co/abr-6024/indian-address-parser-1.5B-GGUF |
| Dataset (9,000 train / 800 test) | https://huggingface.co/datasets/abr-6024/indian-address-parsing-synthetic |
| Example outputs (static page) | https://huggingface.co/spaces/abr-6024/indian-address-parser |
| Python package | https://pypi.org/project/india-address-parser/ |
| npm package | https://www.npmjs.com/package/india-address-parser |

```
pip install india-address-parser     # Python, runs the GGUF with llama-cpp-python
npm install india-address-parser     # Node, talks to a local Ollama server
```

## Results (published v3)

Held-out synthetic test, exact match after lower-casing and removing `.` and `,`:

| Slice | Full-record match |
|---|---|
| All (800) | 94.4% |
| Localities never seen (300) | 94.7% |
| Six districts never seen (200) | 93.0% |

Hand-written checks: 29/30 on Tamil Nadu addresses; 80.6% on 36 mixed-India addresses (part of that gap is the
`city` convention below). The Tamil Nadu set was written by the author using the generator's conventions, so it is
not an independent benchmark.

**Accuracy on real customer addresses has not been measured and is likely lower.** The text is synthetic; only the
geography is real. Evaluate on your own data before relying on it.

### An outside check

I scored the model on 200 labelled addresses from the MIT-licensed
[bharataddress](https://github.com/Neelagiri65/bharataddress) gold set, converted to this project's labels
(evaluation only, never trained on). Full-record match was **35%**. Most of the gap is label convention
(`street` and `city` mean different things there), but `state` 96.5%, `flat` 95.5%, `pincode` 98.5% are the fields
that compare fairly. Treat 35% as a floor for real-world addresses, not a headline score.

### Known weak spot

Bare-number addresses such as `15 Gandhi Salai, Tirupur 641601` can lose the house number. I trained a v4 with more
of that style: it fixed `flat` on bare-number synthetic addresses (98.7% to 100%) but did not fix that example and
was worse on the outside set (35.0% to 31.0%, `state` and `city`), so I kept v3.

## Conventions

- `city` is the **district** (or the metro for big cities), not necessarily the town written in the address.
- `area` is the locality / village / post-office name. `flat` is the door or house number only.
- Anything not written stays an empty string; the model is trained not to guess a city that is not stated.

## Repository layout

```
data/        gen_data.py (synthetic generator), prep_geo.py (builds the geography file), 100-row samples, hand-written sets
training/    train.py (LoRA recipe), eval.py (exact-match scoring, per-field and per-tag)
gguf/        convert.sh (llama.cpp conversion + quantization), eval_gguf.py
packages/    python/ (PyPI) and npm/ (npm) clients
showcase/    build.py for the static example page
```

The full dataset lives on Hugging Face; this repo only keeps small samples.

## Reproduce

```
python data/prep_geo.py pincode.csv                      # needs the India Post pincode CSV (see Data below)
python data/gen_data.py --geo geo/geo_india.json --n-train 9000 --n-test 800
python training/train.py                                  # about an hour on a free Colab T4
python training/eval.py --model merged --test test.jsonl --out results.json
```

Training recipe: LoRA r=16, alpha=32, all linear layers; 2 epochs, 9,000 examples, learning rate 2e-4, completion-only
loss, fp16.

## Data

Locality, pincode, district and state come from the **All India Pincode Directory**, Department of Posts, Government
of India, published on data.gov.in under the Government Open Data License – India (GODL-India), obtained via the
`dropdevrahul/pincodes-india` mirror. Check the current terms at data.gov.in before reuse. House numbers, building,
street and landmark names, phone numbers and wording are generated; no real person's data is included.

Kaggle and GitHub searches turned up pincode directories but no large labelled set of messy address text to train on.
The one labelled set I found (bharataddress, MIT) is small, so it is used only for evaluation.

## Limitations

- Synthetic text over real geography; real-world accuracy is unmeasured.
- Pincodes are extracted, not validated against the locality.
- English / Latin script only.

## License

Code and model weights: Apache-2.0 (weights inherit it from Qwen2.5-1.5B-Instruct; thanks to the Qwen team).
