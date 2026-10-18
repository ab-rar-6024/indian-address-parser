"""Clean the India Post 'All India Pincode Directory' into geo/geo_india.json.

Source: Department of Posts, Government of India, via data.gov.in
        (Government Open Data License - India). Mirror used:
        https://github.com/dropdevrahul/pincodes-india (pincode.csv, 157k rows)

Output rows: [locality, pincode, district, state, office_type]
Usage: python prep_geo.py path/to/pincode.csv
"""
import csv
import json
import re
import sys

SUFFIX = re.compile(r"\s*\(?\b(?:B\.?\s?O\.?|S\.?\s?O\.?|H\.?\s?O\.?|G\.?\s?P\.?\s?O\.?|P\.?\s?O\.?)\)?\s*$", re.I)
PAREN = re.compile(r"\s*\([^)]*\)")
GOOD = re.compile(r"^[A-Za-z][A-Za-z .'\-]{2,29}$")

STATE_FIX = {"JAMMU & KASHMIR": "Jammu and Kashmir", "ANDAMAN & NICOBAR ISLANDS": "Andaman and Nicobar Islands",
             "DADRA & NAGAR HAVELI": "Dadra and Nagar Haveli", "DAMAN & DIU": "Daman and Diu",
             "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "Dadra and Nagar Haveli and Daman and Diu"}


def clean_locality(name):
    n = PAREN.sub("", name or "").strip()
    n = SUFFIX.sub("", n).strip(" .-")
    n = re.sub(r"\s+", " ", n)
    return n.title() if n.isupper() or n.islower() else n


def main(path, out="geo/geo_india.json"):
    rows, seen, rejected = [], set(), 0
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            loc = clean_locality(r["OfficeName"])
            pin = (r["Pincode"] or "").strip()
            if not GOOD.match(loc) or not re.fullmatch(r"\d{6}", pin):
                rejected += 1
                continue
            state = r["StateName"].strip().upper()
            state = STATE_FIX.get(state, state.title())
            state = re.sub(r"^The ", "", state).replace(" And ", " and ")
            district = r["District"].strip().title()
            key = (loc.lower(), pin)
            if key in seen:
                continue
            seen.add(key)
            rows.append([loc, pin, district, state, r["OfficeType"].strip()])
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    tn = sum(1 for r in rows if r[3] == "Tamil Nadu")
    print(f"kept {len(rows)} (rejected {rejected}), Tamil Nadu {tn}, "
          f"states {len({r[3] for r in rows})}, districts {len({(r[3], r[2]) for r in rows})}")


if __name__ == "__main__":
    main(sys.argv[1])
