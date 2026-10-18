"""Indian address -> JSON dataset generator (v3, grounded in real geography).

What is real here: locality, pincode, district and state come from the India Post
"All India Pincode Directory" (Dept. of Posts, Govt. of India, via data.gov.in,
Government Open Data License - India), cleaned by prep_geo.py. A generated address always
uses a (locality, pincode, district, state) combination that exists in that file, so the
model learns real pincode <-> district <-> state relationships, with Tamil Nadu
over-sampled (45%).

What is synthetic: house numbers, building / street / landmark names, phone numbers, the
wording and the noise. No real person's data is used.

Conventions: city = district name (or the metro name for big cities); area = the
locality / village / post-office name; flat = the house/door/plot number only.

Test tags: in_pool = drawn from the same locality pool as training (most still never trained on);
Held out of training (see the 'tag' on test rows):
  unseen_office    localities never seen in training (districts seen)
  unseen_district  six whole districts never seen in training

Usage: python gen_data.py --geo geo/geo_india.json --n-train 9000 --n-test 800
"""
import argparse
import json
import random
import zlib

SYSTEM = (
    "You are an Indian address parser. Convert the address into JSON with exactly these keys: "
    "flat, building, street, landmark, area, city, state, pincode, phone. "
    "Use an empty string for anything missing. Output only JSON."
)
FIELDS = ["flat", "building", "street", "landmark", "area", "city", "state", "pincode", "phone"]

HELD_DISTRICTS = {("Tamil Nadu", "Ariyalur"), ("Tamil Nadu", "Tenkasi"), ("Karnataka", "Udupi"),
                  ("Kerala", "Wayanad"), ("Maharashtra", "Satara"), ("Uttar Pradesh", "Mathura")}

METRO = {"Bangalore Urban": "Bengaluru", "Bangalore": "Bengaluru", "Bengaluru Urban": "Bengaluru",
         "Mumbai": "Mumbai", "Mumbai Suburban": "Mumbai", "Mumbai City": "Mumbai",
         "New Delhi": "Delhi", "Central Delhi": "Delhi", "South Delhi": "Delhi", "North Delhi": "Delhi",
         "East Delhi": "Delhi", "West Delhi": "Delhi", "North West Delhi": "Delhi", "South West Delhi": "Delhi",
         "Greater Mumbai": "Mumbai"}

CITY_ALIASES = {
    "Bengaluru": ["Bangalore", "Bengaluru", "Blr"], "Mumbai": ["Bombay", "Mumbai"], "Delhi": ["New Delhi", "Delhi"],
    "Kochi": ["Cochin", "Kochi"], "Kolkata": ["Calcutta", "Kolkata"], "Chennai": ["Chennai", "Madras"],
    "Thiruvananthapuram": ["Trivandrum", "Thiruvananthapuram"], "Mysuru": ["Mysore", "Mysuru"],
    "Mangaluru": ["Mangalore", "Mangaluru"], "Visakhapatnam": ["Vizag", "Visakhapatnam"],
    "Prayagraj": ["Allahabad", "Prayagraj"], "Varanasi": ["Benares", "Varanasi"],
    "Puducherry": ["Pondicherry", "Puducherry"], "Gurugram": ["Gurgaon", "Gurugram"],
    "Vadodara": ["Baroda", "Vadodara"], "Tiruchirappalli": ["Trichy", "Tiruchirappalli", "Tiruchi"],
    "Kozhikode": ["Calicut", "Kozhikode"], "Tuticorin": ["Thoothukudi", "Tuticorin"],
    "Kanchipuram": ["Kancheepuram", "Kanchipuram"], "Villupuram": ["Viluppuram", "Villupuram"],
    "Tirunelveli": ["Nellai", "Tirunelveli"], "Thiruvallur": ["Tiruvallur", "Thiruvallur"],
    "Coimbatore": ["Kovai", "Coimbatore"], "Kanniyakumari": ["Kanyakumari", "Kanniyakumari"],
    "Tiruppur": ["Tirupur", "Tiruppur"], "Thanjavur": ["Tanjore", "Thanjavur"],
    "Tiruvannamalai": ["Thiruvannamalai", "Tiruvannamalai"], "Pudukkottai": ["Pudukottai", "Pudukkottai"],
    "Nagapattinam": ["Nagapatnam", "Nagapattinam"], "Thiruvarur": ["Tiruvarur", "Thiruvarur"],
}
STATE_ABBR = {
    "Tamil Nadu": "TN", "Maharashtra": "MH", "Delhi": "DL", "Karnataka": "KA", "Telangana": "TS",
    "West Bengal": "WB", "Gujarat": "GJ", "Rajasthan": "RJ", "Kerala": "KL", "Uttar Pradesh": "UP",
    "Chandigarh": "CH", "Madhya Pradesh": "MP", "Bihar": "BR", "Andhra Pradesh": "AP", "Haryana": "HR",
    "Uttarakhand": "UK", "Assam": "AS", "Odisha": "OD", "Jharkhand": "JH", "Chhattisgarh": "CG",
    "Goa": "GA", "Himachal Pradesh": "HP", "Punjab": "PB", "Puducherry": "PY",
}

SYL = ["ra", "ja", "ka", "ma", "na", "sa", "ta", "vi", "su", "an", "ku", "ha", "pu", "ni", "la", "bha",
       "dha", "gha", "shi", "mu", "re", "ti", "ko", "pa", "ga", "da", "ba", "sha", "lak", "ram", "kri", "sri"]
AREA_SUFFIX = ["Nagar", "Colony", "Puram", "Pet", "Vihar", "Layout", "Extension", "Garden", "Enclave", "Park", "Ganj", "Nilayam"]

BUILDING_PREFIX = ["Sri Sai", "Lakshmi", "Green Park", "Royal", "Sunshine", "Krishna", "Ganesh", "Pearl", "Rose Garden",
                   "Skyline", "Shanti", "Om Sai", "Balaji", "Maple", "Galaxy", "Orchid", "Kailash", "Vasant", "Mangal",
                   "Raj", "Ashirwad", "Sunrise", "Gokul", "Kaveri", "Palm Grove", "Blue Ridge", "Heritage", "Lotus",
                   "Sri Murugan", "Amman", "Thirumagal", "Vinayaga", "Pavithra", "Ramakrishna", "Meenakshi",
                   "Sri Venkatesa", "Annai", "Thenral", "Poompuhar", "Sri Rama", "Karpagam", "Tamilselvi"]
BUILDING_SUFFIX = ["Apartments", "Residency", "Towers", "Heights", "Enclave", "Villa", "Complex", "Nivas", "Bhavan",
                   "Society", "CHS", "Flats", "Illam", "Nilayam", "Mansion"]
BUILDING_ABBR = {
    "Apartments": ["apts", "apartment", "apt"], "Residency": ["resi", "residency"], "Towers": ["twr", "towers"],
    "Heights": ["hts", "heights"], "Enclave": ["encl", "enclave"], "Society": ["soc", "society"],
    "Flats": ["flats", "flat"],
}

STREET_NAME = ["Gandhi", "Nehru", "MG", "Anna", "Temple", "Market", "Church", "Station", "Main Bazaar", "Lake View",
               "Bharathi", "Tagore", "Patel", "Ambedkar", "Subhash", "Rajaji", "Kamaraj", "Vivekananda", "Shivaji",
               "Nethaji", "Ring", "Park", "Boring", "Vellore", "Mount", "Hospital", "College",
               # Tamil Nadu street vocabulary
               "Periyar", "Bharathiyar", "Thiruvalluvar", "Mettu", "Pillaiyar Koil", "Perumal Koil", "Amman Koil",
               "North Car", "South Car", "East Car", "West Car", "Vinayagar Koil", "Mariamman Koil", "Court",
               "Railway Feeder", "Collector Office", "Kamarajar", "Bazaar", "School", "Pallivasal"]
STREET_TYPE = ["Road", "Street", "Main Road", "Cross Street", "Lane", "Marg", "Salai", "Path", "Veedhi"]
STREET_ABBR = {"Road": ["rd", "road"], "Street": ["st", "street"], "Lane": ["ln", "lane"], "Marg": ["marg", "mg"],
               "Main": ["main", "mn"], "No": ["No.", "No", "no"]}

DEITY = ["Hanuman", "Murugan", "Ganesh", "Sai Baba", "Shiva", "Balaji", "Durga", "Krishna", "Lakshmi", "Venkateswara",
         "ISKCON", "Ayyappa", "Jagannath", "Ram", "Pillayar", "Mariamman", "Perumal", "Amman", "Vinayagar",
         "Karumariamman", "Angalamman", "Sivan"]
LANDMARK_FIXED = ["Metro Station", "Bus Stand", "Post Office", "Petrol Pump", "Railway Station", "Community Hall",
                  "Big Temple", "Police Station", "Water Tank", "Town Hall", "Museum", "Taluk Office",
                  "Panchayat Union Office", "Collectorate", "Anna Statue", "Ration Shop", "Kalyana Mandapam",
                  "Primary Health Centre", "Cooperative Bank", "Government Hospital", "Government School",
                  "Government College", "Court", "RTO Office", "Bus Depot"]
INST = ["Government", "City", "Apollo", "Fortis", "SBI", "HDFC", "Canara", "DAV", "Kendriya", "St. Mary's", "Rainbow",
        "Indian Bank", "Lakshmi Vilas", "Karur Vysya", "Tamilnad Mercantile"]
PLACE_KIND = ["Temple", "Mandir", "Park", "Hospital", "School", "Bank", "Mall", "Market", "College", "Church", "Masjid"]
LANDMARK_ABBR = {"Hospital": ["hosp", "hospital"], "Government": ["govt", "government"], "Station": ["stn", "station"]}
LANDMARK_PREFIX = ["near", "nr", "opp", "opp.", "behind", "next to", "beside", "near by", "landmark:"]
PERSON = ["Ramesh Kumar", "Suresh Babu", "Anitha Raj", "Mohammed Irfan", "Priya Sharma", "Gurpreet Singh",
          "Lakshmi Narayanan", "Vikram Patel", "Sunita Devi", "Arjun Reddy", "Fatima Begum", "Joseph Thomas",
          "Murugan S", "Kavitha R", "Selvam P", "Rajeswari K", "Palanisamy M"]
TYPO_OK = {"Apartments", "Residency", "Hospital", "Temple", "Street", "Road", "Colony", "Station", "Complex",
           "Heights", "Towers", "Government", "Enclave", "Market", "School", "Park", "Village", "District"}


def split_pool(pool, seed):
    items = sorted(set(pool))
    random.Random(seed).shuffle(items)
    k = max(1, int(len(items) * 0.15))
    return items[k:], items[:k]


def synth(rng):
    return "".join(rng.choice(SYL) for _ in range(rng.randint(2, 3))).capitalize()


def city_of(district, state):
    if district in METRO:
        return METRO[district]
    return district


def is_test_office(locality, pincode):
    """Deterministic ~15% of localities are held out of training."""
    return zlib.crc32(f"{locality.lower()}|{pincode}".encode()) % 100 < 15


def build_pools(geo_rows):
    rng = random.Random(7)
    buildings = ({f"{p} {s}" for p in BUILDING_PREFIX for s in BUILDING_SUFFIX}
                 | {f"{synth(rng)} {rng.choice(BUILDING_SUFFIX)}" for _ in range(300)})
    streets = ({f"{n} {t}" for n in STREET_NAME for t in STREET_TYPE}
               | {f"{synth(rng)} {rng.choice(STREET_TYPE)}" for _ in range(250)})
    landmarks = ({f"{d} {k}" for d in DEITY for k in ("Temple", "Mandir", "Kovil")}
                 | {f"{i} {k}" for i in INST for k in ("Hospital", "Bank", "School")}
                 | set(LANDMARK_FIXED) | {f"{synth(rng)} {rng.choice(PLACE_KIND)}" for _ in range(200)})
    synth_areas = {f"{synth(rng)} {rng.choice(AREA_SUFFIX)}" for _ in range(400)}

    pools = {"train": {}, "test": {}}
    for key, items, seed in (("building", buildings, 1), ("street", streets, 2), ("landmark", landmarks, 3),
                             ("synth_area", synth_areas, 4)):
        pools["train"][key], pools["test"][key] = split_pool(items, seed)

    seen, unseen_office, unseen_district = [], [], []
    for loc, pin, dist, state, otype in geo_rows:
        if (state, dist) in HELD_DISTRICTS:
            unseen_district.append((loc, pin, dist, state, otype))
        elif is_test_office(loc, pin):
            unseen_office.append((loc, pin, dist, state, otype))
        else:
            seen.append((loc, pin, dist, state, otype))
    return pools, {"seen": seen, "unseen_office": unseen_office, "unseen_district": unseen_district}


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def make_flat(rng):
    return rng.choice([
        lambda: f"{rng.randint(1, 20)}{rng.choice('ABCD')}",
        lambda: str(rng.randint(1, 999)),
        lambda: f"{rng.choice('ABCDT')}-{rng.randint(1, 1204)}",
        lambda: f"{rng.randint(1, 99)}/{rng.randint(1, 20)}",
        lambda: f"{rng.randint(1, 9)}-{rng.randint(1, 99)}-{rng.randint(1, 999)}",
    ])()


def make_street(rng, pool):
    r = rng.random()
    if r < 0.55:
        return rng.choice(pool)
    if r < 0.8:
        return f"{ordinal(rng.randint(1, 12))} {rng.choice(['Cross', 'Main', 'Street'])}"
    return rng.choice([f"Road No {rng.randint(1, 60)}", f"Lane {rng.randint(1, 15)}"])


def noisy(text, abbr, rng, p_abbr=0.6, p_typo=0.06):
    out = []
    for w in text.split():
        if w in abbr and rng.random() < p_abbr:
            w = rng.choice(abbr[w])
        elif w in TYPO_OK and len(w) > 4 and rng.random() < p_typo:
            i = rng.randrange(1, len(w) - 1)
            w = w[:i] + w[i + 1:] if rng.random() < 0.5 else w[:i] + w[i + 1] + w[i] + w[i + 2:]
        out.append(w)
    return " ".join(out)


def make_record(rng, pool, office):
    loc, pin, dist, state, otype = office
    city = city_of(dist, state)
    truth = {k: "" for k in FIELDS}
    truth["area"] = loc if rng.random() < 0.8 else ""
    truth["city"] = city
    truth["state"] = state
    truth["pincode"] = pin if rng.random() < 0.85 else ""
    if rng.random() < 0.9:
        truth["flat"] = make_flat(rng)
    if rng.random() < 0.65:
        truth["building"] = rng.choice(pool["building"])
    if rng.random() < 0.65:
        truth["street"] = make_street(rng, pool["street"])
    if rng.random() < 0.5:
        truth["landmark"] = rng.choice(pool["landmark"])
    if rng.random() < 0.6:
        truth["phone"] = str(rng.randint(6, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(9))

    omit_city = rng.random() < 0.1
    if omit_city:
        # city not written: only keep what is actually stated or derivable from the pincode
        truth["city"] = ""
        if not truth["pincode"]:
            truth["state"] = ""

    rural = state == "Tamil Nadu" and otype == "BO" and truth["area"] and rng.random() < 0.4
    tokens = []
    if rng.random() < 0.08:
        tokens.append(rng.choice(["C/o", "S/o", "W/o"]) + " " + rng.choice(PERSON))
    if truth["flat"]:
        if rng.random() < 0.08:
            old = rng.randint(1, 90)
            tokens.append(f"Old No {old}, New No {truth['flat']}")
        else:
            fmt = rng.choice(["Flat {}", "Flat No {}", "Flat No. {}", "#{}", "{}", "{}", "{}", "H.No {}", "No {}",
                              "Door No {}", "D.No {}", "D.No. {}", "Plot {}", "Plot No {}", "House {}", "Shop {}",
                              "Villa {}", "S.No {}"])
            tokens.append(fmt.format(truth["flat"]))
    if truth["building"]:
        tokens.append(noisy(truth["building"], BUILDING_ABBR, rng))
    if truth["street"]:
        tokens.append(noisy(truth["street"], STREET_ABBR, rng))
    landmark_tok = None
    if truth["landmark"]:
        landmark_tok = rng.choice(LANDMARK_PREFIX) + " " + noisy(truth["landmark"], LANDMARK_ABBR, rng)

    area_tokens = []
    if truth["area"]:
        if rural:
            area_tokens = [f"{loc} Village", rng.choice([f"{loc} Post", f"{loc} (PO)", f"{loc} P.O"])]
        else:
            area_tokens = [loc]
    if landmark_tok and rng.random() < 0.2:
        tokens += area_tokens + [landmark_tok]
    else:
        if landmark_tok:
            tokens.append(landmark_tok)
        tokens += area_tokens

    if not omit_city:
        city_tok = rng.choice(CITY_ALIASES.get(city, [city]))
        if rural:
            city_tok = f"{city_tok} " + rng.choice(["District", "Dist", "Dt"])
        tokens.append(city_tok)
    if rng.random() < 0.5 and (truth["state"] or not omit_city):
        tokens.append(state if rng.random() < 0.6 else STATE_ABBR.get(state, state))
        if omit_city and not truth["state"]:
            truth["state"] = state

    sep = rng.choice([", ", ", ", " ", ",", " , "])
    text = sep.join(tokens)
    if truth["pincode"]:
        pc = truth["pincode"]
        pc_tok = rng.choice([pc, pc, f"pin {pc}", f"PIN-{pc}", f"{pc[:3]} {pc[3:]}"])
        text += (" - " if rng.random() < 0.25 else sep) + pc_tok
    if truth["phone"]:
        p = truth["phone"]
        ph = rng.choice([p, f"+91 {p}", f"{p[:5]} {p[5:]}", f"ph {p}", f"mob: {p}", f"Ph.No {p}"])
        text = f"{ph} {text}" if rng.random() < 0.2 else f"{text} {ph}"

    style = rng.choice(["asis", "asis", "lower", "upper"])
    if style == "lower":
        text = text.lower()
    elif style == "upper":
        text = text.upper()
    return text, truth


def generate(n, pool, offices, seed, tag, exclude=frozenset(), tn_frac=0.45):
    rng = random.Random(seed)
    tn = [o for o in offices if o[3] == "Tamil Nadu"]
    other = [o for o in offices if o[3] != "Tamil Nadu"]
    rows, taken = [], set(exclude)
    while len(rows) < n:
        pool_o = tn if (tn and rng.random() < tn_frac) or not other else other
        text, truth = make_record(rng, pool, rng.choice(pool_o))
        if text in taken:
            continue
        taken.add(text)
        rows.append({
            "prompt": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
            "completion": [{"role": "assistant", "content": json.dumps(truth, ensure_ascii=False)}],
            "truth": truth,
            "tag": tag,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default="geo/geo_india.json")
    ap.add_argument("--n-train", type=int, default=9000)
    ap.add_argument("--n-test", type=int, default=800)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    geo = json.load(open(args.geo, encoding="utf-8"))
    pools, offices = build_pools(geo)
    train = generate(args.n_train, pools["train"], offices["seen"], seed=42, tag="train")
    taken = {r["prompt"][1]["content"] for r in train}
    n_seen, n_uo = int(args.n_test * 0.375), int(args.n_test * 0.375)
    test = (generate(n_seen, pools["test"], offices["seen"], 4242, "in_pool", taken)
            + generate(n_uo, pools["test"], offices["unseen_office"], 4243, "unseen_office", taken)
            + generate(args.n_test - n_seen - n_uo, pools["test"], offices["unseen_district"], 4244,
                       "unseen_district", taken))
    random.Random(1).shuffle(test)
    for name, rows in (("train", train), ("test", test)):
        with open(f"{args.out}/{name}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"train={len(train)} test={len(test)} | offices seen/unseen_office/unseen_district = "
          f"{len(offices['seen'])}/{len(offices['unseen_office'])}/{len(offices['unseen_district'])}")
    tn_rows = [r for r in train if r["truth"]["state"] == "Tamil Nadu"]
    print(f"Tamil Nadu share of train: {len(tn_rows) / len(train):.0%}")
    for r in test[:6]:
        print("\nIN :", r["prompt"][1]["content"])
        print("OUT:", r["completion"][0]["content"], "|", r["tag"])


if __name__ == "__main__":
    main()
