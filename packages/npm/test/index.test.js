"use strict";

const test = require("node:test");
const assert = require("node:assert");
const http = require("node:http");
const { parseAddress, AddressParser, FIELDS, SYSTEM, DEFAULT_MODEL } = require("../index.js");

function fakeOllama(reply, status = 200) {
  const seen = [];
  const server = http.createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      seen.push({ url: req.url, body: JSON.parse(body) });
      res.writeHead(status, { "Content-Type": "application/json" });
      res.end(status === 200 ? JSON.stringify({ message: { role: "assistant", content: reply } }) : "boom");
    });
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve({ server, seen, host: `http://127.0.0.1:${server.address().port}` })));
}

const REPLY = JSON.stringify({ flat: "14/2", street: "Gandhi Road", area: "Pollachi", city: "Coimbatore", state: "Tamil Nadu", pincode: "642001", extra: "x", phone: null });

test("returns exactly nine string fields and drops extras", async () => {
  const { server, host } = await fakeOllama(REPLY);
  try {
    const out = await parseAddress("D.No 14/2, Gandhi Road, Pollachi, Coimbatore - 642001", { host });
    assert.deepStrictEqual(Object.keys(out), FIELDS);
    assert.strictEqual(out.flat, "14/2");
    assert.strictEqual(out.phone, "");
    assert.strictEqual(out.building, "");
    assert.ok(!("extra" in out));
  } finally { server.close(); }
});

test("sends the training system prompt, default model, greedy and JSON mode", async () => {
  const { server, seen, host } = await fakeOllama(REPLY);
  try {
    await new AddressParser({ host }).parse("  some address  ");
    const req = seen[0];
    assert.strictEqual(req.url, "/api/chat");
    assert.strictEqual(req.body.model, DEFAULT_MODEL);
    assert.strictEqual(req.body.format, "json");
    assert.strictEqual(req.body.options.temperature, 0);
    assert.deepStrictEqual(req.body.messages[0], { role: "system", content: SYSTEM });
    assert.strictEqual(req.body.messages[1].content, "some address");
  } finally { server.close(); }
});

test("rejects non-JSON model output and empty input", async () => {
  const bad = await fakeOllama("not json");
  try { await assert.rejects(parseAddress("x", { host: bad.host }), /valid JSON/); } finally { bad.server.close(); }
  await assert.rejects(parseAddress("   "), /empty/);
});

test("reports HTTP errors and an unreachable server clearly", async () => {
  const err = await fakeOllama("", 500);
  try { await assert.rejects(parseAddress("x", { host: err.host }), /HTTP 500/); } finally { err.server.close(); }
  await assert.rejects(parseAddress("x", { host: "http://127.0.0.1:1" }), /could not reach Ollama/);
});
