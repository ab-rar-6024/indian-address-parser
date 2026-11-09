# Contributing

The most useful contribution is an address the model gets wrong.

1. Open a **Wrong parse report** (Issues > New issue). Anonymise names, phone numbers and house numbers first: use made-up values that keep the same shape.
2. Say which fields are wrong and what the correct values are. Conventions: `city` is the district (or metro), `area` is the locality / village / post office, `flat` is the door or house number only, and anything not written stays an empty string.

Reports like these decide what the next version is trained on. Please do not paste real customers' data.

## Code changes

```
pip install --no-deps -e packages/python
pip install pytest httpx fastapi uvicorn "huggingface_hub>=0.23"
python -m pytest -q packages/python/tests      # Python tests (llama.cpp is faked)
cd packages/npm && node --test                 # Node tests
```

CI runs both on every pull request, and builds and smoke-tests the Docker image when the Dockerfile or the Python package changes.
