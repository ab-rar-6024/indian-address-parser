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
