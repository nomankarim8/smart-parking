import re
import unicodedata

BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

BANGLA_CLASS_MAP = {
    "ক": "KA", "খ": "KHA", "গ": "GA", "ঘ": "GHA", "চ": "CHA", "ছ": "CAA",
    "জ": "JA", "ঝ": "JHA", "ট": "TA", "ঠ": "THA", "ড": "DA", "ঢ": "DHA",
    "ত": "TA", "থ": "THA", "দ": "DA", "ধ": "DHA", "ন": "NA", "প": "PA",
    "ফ": "PHA", "ব": "BA", "ভ": "BHA", "ম": "MA", "য": "YA", "র": "RA",
    "ল": "LA", "শ": "SHA", "ষ": "SHA", "স": "SA", "হ": "HA",
}

ENGLISH_CLASS_ALIASES = {
    "A": "A", "E": "A", "H": "HA", "HA": "HA", "L": "LA", "LA": "LA",
    "K": "KA", "KA": "KA", "KH": "KHA", "KHA": "KHA", "G": "GA", "GA": "GA",
    "BH": "BHA", "BHA": "BHA", "GH": "GHA", "GHA": "GHA", "C": "CHA", "CH": "CHA",
    "CHA": "CHA", "CAA": "CAA", "J": "JA", "JA": "JA", "JH": "JHA", "JHA": "JHA",
    "N": "NA", "NA": "NA", "P": "PA", "PA": "PA", "F": "PHA", "PH": "PHA", "PHA": "PHA",
    "B": "BA", "BA": "BA", "M": "MA", "MA": "MA", "R": "RA", "RA": "RA",
    "S": "SA", "SA": "SA", "T": "TA", "TA": "TA", "TH": "THA", "THA": "THA",
    "D": "DA", "DA": "DA", "DH": "DHA", "DHA": "DHA",
}

REGION_ALIASES = {
    "ঢাকা মেট্রো": "DHAKA METRO", "ঢাকা মেট্র": "DHAKA METRO", "ঢাকা": "DHAKA",
    "DHAKA METRO": "DHAKA METRO", "DHAKA METRO.": "DHAKA METRO",
    "CHATTOGRAM METRO": "CHATTOGRAM METRO", "CHITTAGONG METRO": "CHATTOGRAM METRO",
    "SYLHET METRO": "SYLHET METRO", "RAJSHAHI METRO": "RAJSHAHI METRO",
    "KHULNA METRO": "KHULNA METRO", "RANGPUR METRO": "RANGPUR METRO",
    "BARISHAL METRO": "BARISHAL METRO",
}

CLASS_TO_CATEGORY = {
    "A": ("MOTORCYCLE", 1), "HA": ("MOTORCYCLE", 1), "LA": ("MOTORCYCLE", 1),
    "KA": ("CAR", 2), "KHA": ("CAR", 2), "GA": ("CAR", 2), "BHA": ("CAR", 2), "GHA": ("CAR", 2),
    "CHA": ("VAN", 3), "CAA": ("VAN", 3),
    "JA": ("BUS", 4), "JHA": ("BUS", 4),
    "TA": ("TRUCK", 5), "THA": ("TRUCK", 5), "DA": ("TRUCK", 5), "DHA": ("TRUCK", 5),
}


def clean(raw: str) -> str:
    text = unicodedata.normalize("NFC", raw or "")
    text = text.replace("—", "-").replace("–", "-").replace("_", "-").replace("/", "-").replace("|", " ").replace("।", " ")
    text = text.translate(BANGLA_DIGITS).upper()
    text = re.sub(r"[^A-Z0-9\u0980-\u09FF\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*-\s*", "-", text)
    return text.strip()


def bangla_class_to_english(value: str) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value in BANGLA_CLASS_MAP:
        return BANGLA_CLASS_MAP[value]
    return ENGLISH_CLASS_ALIASES.get(value.upper())


def canonical_region(value: str) -> str:
    value = clean(value)
    return REGION_ALIASES.get(value, value)


def infer_category(class_code: str | None):
    return CLASS_TO_CATEGORY.get(class_code or "", (None, None))


def parse_plate(raw_text: str) -> dict:
    original = raw_text or ""
    cleaned = clean(original)
    empty = {
        "raw_text": original, "normalized_plate": cleaned, "region_name": "", "class_bn": "",
        "class_code": "", "series_number": "", "vehicle_number": "", "vehicle_category": None,
        "suggested_category_id": None, "valid": False,
    }
    if not cleaned:
        return empty

    # OCR often separates the region/class/number with spaces or hyphens.
    tokens = cleaned.replace("-", " ").split()
    pair_index = None
    for i in range(len(tokens) - 1):
        if re.fullmatch(r"\d{2}", tokens[i]) and re.fullmatch(r"\d{4}", tokens[i + 1]):
            pair_index = i
            break

    if pair_index is None:
        # Try to recover a four-digit number immediately preceded by a two-digit series.
        for i, token in enumerate(tokens):
            if re.fullmatch(r"\d{4}", token):
                for j in range(max(0, i - 3), i):
                    if re.fullmatch(r"\d{2}", tokens[j]):
                        pair_index = j
                        break
                if pair_index is not None:
                    break

    if pair_index is None:
        return empty

    series = tokens[pair_index]
    vehicle_number = tokens[pair_index + 1]
    prefix_tokens = tokens[:pair_index]
    class_bn = ""
    class_code = ""
    if prefix_tokens:
        candidate = prefix_tokens[-1]
        mapped = bangla_class_to_english(candidate)
        if mapped:
            if re.search(r"[\u0980-\u09FF]", candidate):
                class_bn = candidate
            class_code = mapped
            prefix_tokens = prefix_tokens[:-1]

    region = canonical_region(" ".join(prefix_tokens))
    category, category_id = infer_category(class_code)
    parts = [p for p in [region, class_code] if p]
    normalized_plate = ((" ".join(parts) + f" {series}-{vehicle_number}").strip())

    return {
        "raw_text": original,
        "normalized_plate": normalized_plate,
        "region_name": region,
        "class_bn": class_bn,
        "class_code": class_code,
        "series_number": series,
        "vehicle_number": vehicle_number,
        "vehicle_category": category,
        "suggested_category_id": category_id,
        "valid": bool(region and class_code and series and vehicle_number),
    }


def normalize(raw: str) -> str:
    parsed = parse_plate(raw)
    return parsed["normalized_plate"] if parsed["valid"] else clean(raw)
