import argparse
import json
import sys

from . import __version__
from .parser import AddressParser


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "serve":
        try:
            from .server import main as serve
        except ImportError:
            sys.exit('the HTTP server needs extra packages: pip install "india-address-parser[server]"')
        return serve(argv[1:])
    ap = argparse.ArgumentParser(prog="india-address-parser",
                                 description="Parse Indian addresses into JSON with a local model. "
                                             "Run `india-address-parser serve --help` for the HTTP API.")
    ap.add_argument("address", nargs="*", help="address text; if omitted, one address per line is read from stdin")
    ap.add_argument("--model", help="path to a local .gguf file (default: download Q4_K_M from Hugging Face)")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    addresses = [" ".join(args.address)] if args.address else [l.strip() for l in sys.stdin if l.strip()]
    if not addresses:
        ap.error("no address given")
    parser = AddressParser(model_path=args.model)
    for a in addresses:
        print(json.dumps(parser.parse(a), ensure_ascii=False))


if __name__ == "__main__":
    main()
