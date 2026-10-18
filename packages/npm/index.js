"use strict";

const FIELDS = ["flat", "building", "street", "landmark", "area", "city", "state", "pincode", "phone"];

// Must match the system prompt the model was trained with.
const SYSTEM =
  "You are an Indian address parser. Convert the address into JSON with exactly these keys: " +
  "flat, building, street, landmark, area, city, state, pincode, phone. " +
  "Use an empty string for anything missing. Output only JSON.";

const DEFAULT_MODEL = "hf.co/abr-6024/indian-address-parser-1.5B-GGUF:Q4_K_M";
const DEFAULT_HOST = "http://127.0.0.1:11434";

function clean(raw) {
  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    throw new Error("model did not return valid JSON: " + JSON.stringify(raw));
  }
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("model returned JSON that is not an object: " + JSON.stringify(raw));
  }
  const out = {};
  for (const k of FIELDS) out[k] = data[k] == null ? "" : String(data[k]);
  return out;
}

async function post(host, path, body) {
  let res;
  try {
    res = await fetch(host.replace(/\/+$/, "") + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw new Error(`could not reach Ollama at ${host} (is it running? https://ollama.com): ${err.message}`);
  }
  if (!res.ok) throw new Error(`Ollama returned HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

/**
 * Parse one Indian address with a local Ollama server.
 * Returns an object with flat, building, street, landmark, area, city, state, pincode, phone (empty string if missing).
 * `city` is the district (or metro) name.
 */
async function parseAddress(address, options = {}) {
  if (typeof address !== "string" || !address.trim()) throw new Error("address is empty");
  const { host = DEFAULT_HOST, model = DEFAULT_MODEL } = options;
  const reply = await post(host, "/api/chat", {
    model,
    stream: false,
    format: "json",
    options: { temperature: 0 },
    messages: [
      { role: "system", content: SYSTEM },
      { role: "user", content: address.trim() },
    ],
  });
  return clean(reply.message && reply.message.content);
}

/** Download the model into Ollama if it is not there yet (about 1 GB, one time). */
async function pullModel(options = {}) {
  const { host = DEFAULT_HOST, model = DEFAULT_MODEL } = options;
  await post(host, "/api/pull", { model, stream: false });
}

class AddressParser {
  constructor(options = {}) {
    this.options = options;
  }
  parse(address) {
    return parseAddress(address, this.options);
  }
  async parseMany(addresses) {
    const out = [];
    for (const a of addresses) out.push(await this.parse(a));
    return out;
  }
}

module.exports = { parseAddress, pullModel, AddressParser, FIELDS, SYSTEM, DEFAULT_MODEL, DEFAULT_HOST, clean };
