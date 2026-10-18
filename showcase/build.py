"""Build index.html for the static showcase Space from saved model outputs (results.json)."""
import html
import json
import sys

FIELDS = ["flat", "building", "street", "landmark", "area", "city", "state", "pincode", "phone"]
res = json.load(open(sys.argv[1], encoding="utf-8"))
e = html.escape


def chips(d):
    parts = [f'<span class="chip"><b>{k}</b> {e(str(v))}</span>' for k, v in d.items() if v and k in FIELDS]
    return " ".join(parts)


def tn_row(x):
    status = '<span class="ok">match</span>' if x["ok"] else '<span class="bad">miss</span>'
    out = chips(x["output"])
    if not x["ok"]:
        diff = [k for k in FIELDS if str(x["output"].get(k, "")).lower() != str(x["truth"].get(k, "")).lower()]
        exp = " ".join(f'<span class="chip"><b>{k}</b> {e(str(x["truth"][k]))}</span>' for k in diff)
        out += f'<div class="exp">expected: {exp}</div>'
    return f'<tr class="{"" if x["ok"] else "miss"}"><td class="inp">{e(x["input"])}</td><td>{out}</td><td>{status}</td></tr>'


def mixed_row(x):
    return f'<tr><td class="inp">{e(x["input"])}</td><td>{chips(x["output"])}</td></tr>'


n_ok = sum(x["ok"] for x in res["tn"])
tn_rows = "\n".join(tn_row(x) for x in res["tn"])
mixed_rows = "\n".join(mixed_row(x) for x in res["mixed"])

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Indian Address Parser</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1f2328; --mute:#5b636b; --card:#ffffff; --line:#e3e0d8; --acc:#b4470f; --ok:#1a7f37; --bad:#b42318; --chip:#f1eee6; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#14161a; --fg:#e8e6e1; --mute:#9aa1a9; --card:#1c1f24; --line:#2c3037; --acc:#f2994a; --ok:#56d364; --bad:#ff7b72; --chip:#262a31; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:980px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-size:2rem; margin:0 0 6px; }}
h2 {{ font-size:1.25rem; margin:36px 0 10px; }}
p {{ margin:8px 0; }}
a {{ color:var(--acc); }}
.lead {{ color:var(--mute); font-size:1.05rem; }}
.links a {{ display:inline-block; margin:6px 10px 0 0; padding:7px 14px; border:1px solid var(--line); border-radius:999px; text-decoration:none; background:var(--card); }}
.note {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--acc); border-radius:8px; padding:12px 14px; margin:18px 0; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:14px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px; }}
.stat b {{ display:block; font-size:1.5rem; }}
.stat span {{ color:var(--mute); font-size:.9rem; }}
.tablewrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--card); }}
table {{ border-collapse:collapse; width:100%; font-size:.93rem; }}
th, td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--mute); font-weight:600; font-size:.82rem; text-transform:uppercase; letter-spacing:.03em; }}
tr:last-child td {{ border-bottom:0; }}
td.inp {{ min-width:230px; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.85rem; }}
.chip {{ display:inline-block; background:var(--chip); border-radius:6px; padding:1px 8px; margin:2px 3px 2px 0; font-size:.85rem; }}
.chip b {{ color:var(--mute); font-weight:600; margin-right:4px; }}
.ok {{ color:var(--ok); font-weight:600; }} .bad {{ color:var(--bad); font-weight:600; }}
tr.miss td {{ background:color-mix(in srgb, var(--bad) 8%, transparent); }}
.exp {{ margin-top:4px; color:var(--mute); font-size:.85rem; }}
pre {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; overflow-x:auto; font-size:.85rem; }}
ul {{ padding-left:20px; }} li {{ margin:4px 0; }}
footer {{ margin-top:40px; color:var(--mute); font-size:.88rem; }}
</style>
</head>
<body>
<main>
<h1>Indian Address Parser</h1>
<p class="lead">A 1.5B model fine-tuned from Qwen2.5-1.5B-Instruct. It turns a messy Indian address into
structured JSON: flat, building, street, landmark, area, city, state, pincode, phone.</p>
<div class="links">
<a href="https://huggingface.co/abr-6024/indian-address-parser-1.5B">Model</a>
<a href="https://huggingface.co/datasets/abr-6024/indian-address-parsing-synthetic">Dataset and generator</a>
<a href="https://huggingface.co/abr-6024/indian-address-parser-1.5B-GGUF">GGUF (runs on a laptop)</a>
<a href="https://pypi.org/project/india-address-parser/">pip</a>
<a href="https://www.npmjs.com/package/india-address-parser">npm</a>
</div>

<div class="note"><b>This page is a showcase, not a live demo.</b> Every output below is a real, saved result from
the published model, run once with greedy decoding. You cannot type an address here. To try your own addresses,
use the code at the bottom or the model page.</div>

<h2>Scores</h2>
<div class="stats">
<div class="stat"><b>94.4%</b><span>full-record match, 800 synthetic test addresses</span></div>
<div class="stat"><b>93.0%</b><span>on six districts never seen in training</span></div>
<div class="stat"><b>{n_ok} / {len(res["tn"])}</b><span>hand-written Tamil Nadu addresses (below)</span></div>
<div class="stat"><b>80.6%</b><span>36 mixed-India hand-written addresses (partly a label-convention gap)</span></div>
</div>
<p>Accuracy on real customer addresses has <b>not</b> been measured and is likely lower. The Tamil Nadu set was
written by the model's author using the generator's conventions, so it is not an independent benchmark.</p>

<h2>Conventions</h2>
<ul>
<li><code>city</code> is the district name, or the metro name for big cities.</li>
<li><code>area</code> is the locality, village or post-office name. <code>flat</code> is the door or house number only.</li>
<li>Anything not written in the address stays empty. The state is filled in when it can be inferred from the city or pincode.</li>
</ul>

<h2>Tamil Nadu examples ({n_ok} of {len(res["tn"])} exactly right)</h2>
<p>Inputs are made-up addresses; phone numbers are fake. Empty fields are hidden. The miss is shown in red with what was expected.</p>
<div class="tablewrap"><table>
<tr><th>Address in</th><th>Model output</th><th>vs my label</th></tr>
{tn_rows}
</table></div>

<h2>Other states (outputs only, no scoring)</h2>
<div class="tablewrap"><table>
<tr><th>Address in</th><th>Model output</th></tr>
{mixed_rows}
</table></div>

<h2>Try it yourself</h2>
<p>Fastest way, on a laptop with no GPU:</p>
<pre>pip install india-address-parser
python -c "from india_address_parser import parse; print(parse('D.No 14/2, Gandhi Road, Pollachi, Coimbatore - 642001'))"</pre>
<p>Node.js: <code>npm install india-address-parser</code> (needs <a href="https://ollama.com">Ollama</a>). The model files are on
<a href="https://huggingface.co/abr-6024/indian-address-parser-1.5B-GGUF">Hugging Face (GGUF)</a>. Or load the original weights with transformers:</p>
<pre>import json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

repo = "abr-6024/indian-address-parser-1.5B"
tok = AutoTokenizer.from_pretrained(repo)
model = AutoModelForCausalLM.from_pretrained(repo, dtype=torch.float16, device_map="auto")

SYSTEM = ("You are an Indian address parser. Convert the address into JSON with exactly these keys: "
          "flat, building, street, landmark, area, city, state, pincode, phone. "
          "Use an empty string for anything missing. Output only JSON.")
msgs = [{{"role": "system", "content": SYSTEM}},
        {{"role": "user", "content": "Flat 3B, Sri Murugan Apartments, Peelamedu, Coimbatore 641004"}}]
ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt").to(model.device)
out = model.generate(ids, max_new_tokens=200, do_sample=False)
print(json.loads(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)))</pre>

<h2>Limitations</h2>
<ul>
<li>Trained on synthetic address text over real India Post geography; real-world accuracy is unmeasured.</li>
<li>Bare-number addresses are a known weak spot (see the miss above).</li>
<li>Pincodes are extracted, not validated against the locality. English / Latin script only.</li>
</ul>

<footer>Contains information from the All India Pincode Directory, Department of Posts, Government of India (data.gov.in, GODL-India).
Base model: Qwen2.5-1.5B-Instruct, Apache-2.0.</footer>
</main>
</body>
</html>
"""
open(sys.argv[2], "w", encoding="utf-8").write(page)
print("wrote", sys.argv[2], len(page), "bytes")
