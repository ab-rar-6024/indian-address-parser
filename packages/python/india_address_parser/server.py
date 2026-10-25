"""HTTP API around AddressParser. Needs the optional extra: pip install "india-address-parser[server]"."""
import argparse
import hmac
import os
import threading
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .parser import FIELDS, AddressParser

MAX_ADDRESS_CHARS = 500
MAX_BATCH = 100


class ParseRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=MAX_ADDRESS_CHARS)


class BatchRequest(BaseModel):
    addresses: List[str] = Field(..., min_length=1, max_length=MAX_BATCH)


def create_app(parser, api_key: Optional[str] = None) -> FastAPI:
    """Build the app around an already-loaded parser (anything with a ``parse(str) -> dict`` method).

    If ``api_key`` is set, every endpoint except /health needs ``Authorization: Bearer <key>``.
    """
    app = FastAPI(title="India Address Parser", version=__version__)
    lock = threading.Lock()  # one llama.cpp context is not thread-safe; requests are served one at a time

    def check_key(authorization: Optional[str] = Header(default=None)):
        if not api_key:
            return
        supplied = authorization[7:] if authorization and authorization.lower().startswith("bearer ") else ""
        if not hmac.compare_digest(supplied.encode(), api_key.encode()):
            raise HTTPException(status_code=401, detail="missing or wrong API key",
                                headers={"WWW-Authenticate": "Bearer"})

    def run(address: str) -> dict:
        if not address.strip():
            raise ValueError("address is empty")
        if len(address) > MAX_ADDRESS_CHARS:
            raise ValueError(f"address is longer than {MAX_ADDRESS_CHARS} characters")
        with lock:
            return parser.parse(address)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__, "fields": FIELDS}

    @app.post("/parse", dependencies=[Depends(check_key)])
    def parse_one(req: ParseRequest):
        try:
            return run(req.address)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/parse_batch", dependencies=[Depends(check_key)])
    def parse_batch(req: BatchRequest):
        results = []
        for address in req.addresses:
            try:
                results.append(run(address))
            except ValueError as exc:
                results.append({"error": str(exc)})  # one bad address does not fail the whole batch
        return {"results": results}

    return app


def main(argv=None):
    ap = argparse.ArgumentParser(prog="india-address-parser serve",
                                 description="Serve the address parser over HTTP.")
    ap.add_argument("--host", default="127.0.0.1", help="interface to bind (default 127.0.0.1; use 0.0.0.0 in Docker)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--model", help="path to a local .gguf file (default: download Q4_K_M from Hugging Face)")
    ap.add_argument("--api-key", default=os.environ.get("ADDRESS_API_KEY"),
                    help="require this bearer token (default: env ADDRESS_API_KEY; none = open)")
    args = ap.parse_args(argv)

    import uvicorn

    if not args.api_key and args.host not in ("127.0.0.1", "localhost", "::1"):
        print("warning: listening on a public interface with no API key; anyone who can reach it can use it")
    parser = AddressParser(model_path=args.model or os.environ.get("ADDRESS_MODEL_PATH"))
    uvicorn.run(create_app(parser, args.api_key), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
