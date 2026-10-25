#!/usr/bin/env node
"use strict";

const { parseAddress, pullModel } = require("../index.js");

const USAGE = `Usage: india-address-parser [--host URL] [--model NAME] [--pull] "<address>"
       india-address-parser --api-url URL [--api-key KEY] "<address>"
       echo "<address>" | india-address-parser

By default needs a running Ollama server (https://ollama.com); use --pull once to download the model (about 1 GB).
With --api-url (or env ADDRESS_API_URL / ADDRESS_API_KEY) it calls an "india-address-parser serve" HTTP server instead.`;

async function readStdin() {
  let text = "";
  for await (const chunk of process.stdin) text += chunk;
  return text.split("\n").map((l) => l.trim()).filter(Boolean);
}

async function main() {
  const args = process.argv.slice(2);
  const options = {};
  if (process.env.ADDRESS_API_URL) options.apiUrl = process.env.ADDRESS_API_URL;
  if (process.env.ADDRESS_API_KEY) options.apiKey = process.env.ADDRESS_API_KEY;
  const words = [];
  let pull = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--host") options.host = args[++i];
    else if (args[i] === "--model") options.model = args[++i];
    else if (args[i] === "--api-url") options.apiUrl = args[++i];
    else if (args[i] === "--api-key") options.apiKey = args[++i];
    else if (args[i] === "--pull") pull = true;
    else if (args[i] === "-h" || args[i] === "--help") { console.log(USAGE); return; }
    else words.push(args[i]);
  }
  if (pull && !options.apiUrl) await pullModel(options);
  const addresses = words.length ? [words.join(" ")] : process.stdin.isTTY ? [] : await readStdin();
  if (!addresses.length) {
    if (pull) return;
    console.error(USAGE);
    process.exit(2);
  }
  for (const a of addresses) console.log(JSON.stringify(await parseAddress(a, options)));
}

main().catch((err) => {
  console.error("error: " + err.message);
  process.exit(1);
});
