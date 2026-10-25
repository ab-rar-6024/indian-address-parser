# Build from the repo root:  docker build -t india-address-parser .
# Run:                       docker run -p 8000:8000 -e ADDRESS_API_KEY=choose-a-secret india-address-parser
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir llama-cpp-python --only-binary=llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

COPY packages/python /src
RUN pip install --no-cache-dir "/src[server]"

# Bake the model into the image (about 1 GB) so the container starts offline.
RUN python -c "from huggingface_hub import hf_hub_download; hf_hub_download('abr-6024/indian-address-parser-1.5B-GGUF', 'indian-address-parser-1.5B-Q4_K_M.gguf', local_dir='/models')"
ENV ADDRESS_MODEL_PATH=/models/indian-address-parser-1.5B-Q4_K_M.gguf

RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["india-address-parser", "serve", "--host", "0.0.0.0", "--port", "8000"]
