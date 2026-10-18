import argparse
import json
import sys

from . import __version__
from .parser import AddressParser


def main(argv=None):
    ap = argparse.ArgumentParser(prog="india-address-parser",
                                 description="Parse Indian addresses into JSON with a local model.")
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
