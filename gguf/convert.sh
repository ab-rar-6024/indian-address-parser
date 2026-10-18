#!/bin/bash
# Convert the published HF model to GGUF (f16 -> Q8_0, Q4_K_M). Run in Colab from /content.
set -e
pip install -q gguf sentencepiece huggingface_hub
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp
pip install -q -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt 2>&1 | tail -2 || true
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("abr-6024/indian-address-parser-1.5B", local_dir="hfmodel", allow_patterns=["*.json", "*.safetensors", "*.jinja"])
PY
mkdir -p out
python llama.cpp/convert_hf_to_gguf.py hfmodel --outfile out/indian-address-parser-1.5B-f16.gguf --outtype f16
cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF >/dev/null
cmake --build llama.cpp/build --target llama-quantize -j"$(nproc)" 2>&1 | tail -2
for q in Q8_0 Q4_K_M; do
  llama.cpp/build/bin/llama-quantize out/indian-address-parser-1.5B-f16.gguf out/indian-address-parser-1.5B-$q.gguf $q
done
ls -la out
