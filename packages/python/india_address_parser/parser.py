"""Parse messy Indian addresses into structured fields with a local GGUF model."""
import json
from typing import Dict, Iterable, List, Optional

FIELDS = ["flat", "building", "street", "landmark", "area", "city", "state", "pincode", "phone"]

# Must match the system prompt the model was trained with.
SYSTEM = ("You are an Indian address parser. Convert the address into JSON with exactly these keys: "
          "flat, building, street, landmark, area, city, state, pincode, phone. "
          "Use an empty string for anything missing. Output only JSON.")

DEFAULT_REPO = "abr-6024/indian-address-parser-1.5B-GGUF"
DEFAULT_FILE = "*Q4_K_M.gguf"


def _clean(raw: str) -> Dict[str, str]:
    """Turn the model's text into a dict with exactly the nine expected string fields."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model did not return valid JSON: {raw!r}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"model returned JSON that is not an object: {raw!r}")
    return {k: "" if data.get(k) is None else str(data[k]) for k in FIELDS}


class AddressParser:
    """Loads the model once; call :meth:`parse` as many times as you like.

    By default the Q4_K_M file (about 1 GB) is downloaded from Hugging Face on first use and cached.
    Pass ``model_path`` to use a local .gguf file instead.
    """

    def __init__(self, model_path: Optional[str] = None, repo_id: str = DEFAULT_REPO,
                 filename: str = DEFAULT_FILE, n_ctx: int = 1024, n_threads: Optional[int] = None,
                 verbose: bool = False):
        try:
            from llama_cpp import Llama
        except ImportError as exc:  # pragma: no cover
            raise ImportError("llama-cpp-python is required: pip install llama-cpp-python") from exc
        kwargs = dict(n_ctx=n_ctx, verbose=verbose)
        if n_threads:
            kwargs["n_threads"] = n_threads
        if model_path:
            self._llm = Llama(model_path=model_path, **kwargs)
        else:
            self._llm = Llama.from_pretrained(repo_id=repo_id, filename=filename, **kwargs)

    def parse(self, address: str) -> Dict[str, str]:
        """Return a dict with keys flat, building, street, landmark, area, city, state, pincode, phone.

        Fields not written in the address are empty strings. ``city`` is the district (or metro) name.
        Raises ValueError if the model output is not a JSON object.
        """
        if not address or not address.strip():
            raise ValueError("address is empty")
        out = self._llm.create_chat_completion(
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": address.strip()}],
            temperature=0.0,
            max_tokens=200,
        )
        return _clean(out["choices"][0]["message"]["content"])

    def parse_many(self, addresses: Iterable[str]) -> List[Dict[str, str]]:
        return [self.parse(a) for a in addresses]


_default: Optional[AddressParser] = None


def parse(address: str) -> Dict[str, str]:
    """Parse one address with a shared default model (downloaded and loaded on the first call)."""
    global _default
    if _default is None:
        _default = AddressParser()
    return _default.parse(address)
