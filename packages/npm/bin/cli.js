#!/usr/bin/env node
"use strict";

const { parseAddress, pullModel } = require("../index.js");

const USAGE = `Usage: india-address-parser [--host URL] [--model NAME] [--pull] "<address>"
       echo "<address>" | india-address-parser

Needs a running Ollama server (https://ollama.com). Use --pull once to download the model (about 1 GB).`;

async function readStdin() {
  let text = "";
  for await (const chunk of process.stdin) text += chunk;
  return text.split("\n").map((l) => l.trim()).filter(Boolean);
}

async function main() {
  const args = process.argv.slice(2);
  const options = {};
  const words = [];
  let pull = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--host") options.host = args[++i];
    else if (args[i] === "--model") options.model = args[++i];
    else if (args[i] === "--pull") pull = true;
    else if (args[i] === "-h" || args[i] === "--help") { console.log(USAGE); return; }
    else words.push(args[i]);
  }
  if (pull) await pullModel(options);
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
