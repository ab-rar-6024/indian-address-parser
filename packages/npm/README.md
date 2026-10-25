# india-address-parser

Parse messy Indian addresses into structured fields with a small local model (1.5B, runs on CPU, no API key).
This package is a small client. It talks either to [Ollama](https://ollama.com) on your machine, or to the
self-hosted HTTP API (`india-address-parser serve`, see below), so a store or email backend needs no Ollama.

```js
const { parseAddress } = require("india-address-parser");

await parseAddress("D.No 14/2, Gandhi Road, Pollachi, Coimbatore - 642001");
// { flat: '14/2', building: '', street: 'Gandhi Road', landmark: '', area: 'Pollachi',
//   city: 'Coimbatore', state: 'Tamil Nadu', pincode: '642001', phone: '' }
```

The model is [abr-6024/indian-address-parser-1.5B](https://huggingface.co/abr-6024/indian-address-parser-1.5B),
a fine-tune of Qwen2.5-1.5B-Instruct, served from its
[GGUF repo](https://huggingface.co/abr-6024/indian-address-parser-1.5B-GGUF).

## Install

1. Install and start [Ollama](https://ollama.com/download).
2. Install the package (Node 18 or newer, no other dependencies):

```
npm install india-address-parser
```

3. Download the model once (Q4_K_M, about 1 GB):

```
npx india-address-parser --pull
```

## Use

```js
import { parseAddress, AddressParser, pullModel } from "india-address-parser";   // ESM
// const { parseAddress, AddressParser, pullModel } = require("india-address-parser");   // CommonJS

await pullModel();                                   // optional; same as the --pull flag
const parser = new AddressParser({ host: "http://127.0.0.1:11434" });
const result = await parser.parse("No 21, East Car Street, Srirangam, Tiruchirappalli 620006");
const many = await parser.parseMany(["12, Mettu Street, Karaikudi, Sivaganga District 630001"]);
```

TypeScript types are included. Options: `host` (Ollama URL) and `model` (Ollama model name; default
`hf.co/abr-6024/indian-address-parser-1.5B-GGUF:Q4_K_M`).

Command line:

```
npx india-address-parser "Flat 6, Kaveri Residency, Gandhipuram, Coimbatore 641012"
cat addresses.txt | npx india-address-parser        # one address per line, one JSON object per line out
```

Every result has exactly these keys: `flat, building, street, landmark, area, city, state, pincode, phone`.
Anything not written in the address is an empty string.

## Without Ollama: use the HTTP API

From Node.js, point the client at that server instead of Ollama:

```js
import { parseAddress, AddressParser } from "india-address-parser";
const opts = { apiUrl: "http://localhost:8000", apiKey: "choose-a-secret" };
await parseAddress("Flat 3B, Sri Murugan Apartments, Peelamedu, Coimbatore 641004", opts);
await new AddressParser(opts).parseMany(["12, Mettu Street, Karaikudi 630001", "..."]);   // one batch request
```

Or from any language, just call `POST /parse`.

Command line: `npx india-address-parser --api-url http://localhost:8000 --api-key choose-a-secret "<address>"`
(or set `ADDRESS_API_URL` and `ADDRESS_API_KEY`). How to run the server: [Python package](https://pypi.org/project/india-address-parser/)
and the [GitHub repo](https://github.com/ab-rar-6024/indian-address-parser).

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
- `parseAddress` rejects if Ollama is not running, or if the model does not return a JSON object.

## Credits and license

Code: Apache-2.0. Base model: Qwen2.5-1.5B-Instruct (Apache-2.0). Training geography: All India Pincode Directory,
Department of Posts, Government of India (data.gov.in, GODL-India).
