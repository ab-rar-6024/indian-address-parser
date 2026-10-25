# india-address-parser

Parse messy Indian addresses into structured fields with a small local model (1.5B, runs on CPU, no API key).

```python
from india_address_parser import parse

parse("D.No 14/2, Gandhi Road, Pollachi, Coimbatore - 642001")
# {'flat': '14/2', 'building': '', 'street': 'Gandhi Road', 'landmark': '', 'area': 'Pollachi',
#  'city': 'Coimbatore', 'state': 'Tamil Nadu', 'pincode': '642001', 'phone': ''}
```

The model is [abr-6024/indian-address-parser-1.5B](https://huggingface.co/abr-6024/indian-address-parser-1.5B),
a fine-tune of Qwen2.5-1.5B-Instruct, run through [llama.cpp](https://github.com/ggml-org/llama.cpp) as a
[GGUF file](https://huggingface.co/abr-6024/indian-address-parser-1.5B-GGUF).

## Install

```
pip install india-address-parser
```

The first call downloads the model (Q4_K_M, about 1 GB) from Hugging Face and caches it. After that it runs offline.
`llama-cpp-python` is installed as a dependency. If pip has to compile it and fails, install a prebuilt CPU wheel first:

```
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

## Use

```python
from india_address_parser import AddressParser

p = AddressParser()                       # loads the model once
p.parse("Flat 3B, Sri Murugan Apartments, Peelamedu, Coimbatore 641004, 9442012345")
p.parse_many(["12, Mettu Street, Karaikudi, Sivaganga District 630001", "..."])

AddressParser(model_path="my.gguf")       # use a local GGUF file instead of downloading
```

Command line:

```
india-address-parser "No 21, East Car Street, Srirangam, Tiruchirappalli 620006"
cat addresses.txt | india-address-parser          # one address per line, one JSON object per line out
```

Every result has exactly these keys: `flat, building, street, landmark, area, city, state, pincode, phone`.
Anything not written in the address is an empty string.

## HTTP API (self-hosted)

Run the model as a small web service, so any backend (Node, PHP, Java, an e-commerce platform, an email pipeline)
can call it over HTTP without Python or Ollama on the caller's side.

```
pip install "india-address-parser[server]"
ADDRESS_API_KEY=choose-a-secret india-address-parser serve --port 8000
```

or with Docker (from the repo root; the image includes the 1 GB model, needs about 2 GB RAM, no GPU):

```
docker build -t india-address-parser .
docker run -p 8000:8000 -e ADDRESS_API_KEY=choose-a-secret india-address-parser
```

```
curl -X POST http://localhost:8000/parse   -H "Authorization: Bearer choose-a-secret" -H "Content-Type: application/json"   -d '{"address": "D.No 14/2, Gandhi Road, Pollachi, Coimbatore - 642001"}'
```

| Endpoint | Body | Returns |
|---|---|---|
| `GET /health` | none | `{"status": "ok", ...}` (no key needed) |
| `POST /parse` | `{"address": "..."}` (up to 500 characters) | the 9 fields |
| `POST /parse_batch` | `{"addresses": ["...", "..."]}` (up to 100) | `{"results": [...]}`; a bad item becomes `{"error": "..."}` |

- Interactive docs are at `/docs`. Errors: `401` wrong or missing key, `422` bad input or unusable model output.
- Requests are handled one at a time (one model instance). Expect roughly 3 seconds per address on a laptop CPU
  and more on small cloud CPUs, so use it for emails, imports and "confirm your address" steps, not to block a checkout.
- The server does not log request bodies, but your reverse proxy might. Addresses are personal data: keep the service
  on your own network or behind HTTPS, and set an API key before binding to `0.0.0.0`.

## Conventions

- `city` is the **district** name (or the metro name for big cities), not necessarily the town written in the address.
- `area` is the locality, village or post-office name. `flat` is the door or house number only.
- The model does not guess a city that is not written. It fills the state when the city or pincode implies it.

## Accuracy and limits

The default file (Q4_K_M) scored 94.0% full-record exact match on 200 random synthetic test addresses, 29 of 30 on a
hand-written Tamil Nadu set and 28 of 36 on a hand-written mixed-India set. The original unquantized model scored
94.4% on all 800 synthetic test addresses. The hand-written sets were written by the model's author, so they are not
independent benchmarks. Details: [GGUF model card](https://huggingface.co/abr-6024/indian-address-parser-1.5B-GGUF).

- The model was trained on synthetic address text over real India Post geography. **Accuracy on real customer
  addresses has not been measured** and is likely lower. Test it on your own data before relying on it.
- Bare-number addresses such as `15 Gandhi Salai, Tirupur` can lose the house number.
- Pincodes are extracted, not validated against the locality. English / Latin script only.
- `parse` raises `ValueError` if the model does not return a JSON object. Handle that in production code.

## Credits and license

Code: Apache-2.0. Base model: Qwen2.5-1.5B-Instruct (Apache-2.0). Training geography: All India Pincode Directory,
Department of Posts, Government of India (data.gov.in, GODL-India).
