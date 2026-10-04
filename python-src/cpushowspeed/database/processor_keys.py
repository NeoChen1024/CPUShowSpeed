"""Versioned processor identity rule `sku-key-v1`: one normalized SKU key from processor text.

Matching against observations happens in `database.processor_identity`; the curated
`processor_sku.keys` hold the keys this rule must produce.
"""

import re

_NOISE = re.compile(r"\((?:r|tm)\)|®|™|\bintel\b|\bamd\b|\bprocessors?\b|\bcpu\b|\b(?:dual|quad|six|multi)-core\b|@.*$", re.I)
_INTEL_MODEL = re.compile(
    r"\b(?:(?P<tier>platinum|gold|silver|bronze|max|w|d|e[357]?)(?:\s+|-))?"
    r"(?P<num>[a-z]?\d{4}[a-z]{0,2})(?:\s+(?P<ver>v\d))?\b",
    re.I,
)
# EPYC models may carry letters inside the number (7H12, 75F3, 4584PX).
_AMD_MODEL = re.compile(r"\b(?P<num>\d(?=(?:[a-z]*\d){1,})[0-9a-z]{2,5})(?:\s+(?P<suffix>se|he|ee))?\b", re.I)


def _clean(text):
    # Trademarks first, then every parenthetical: clocks, buses, caches, sockets ("939-pin") are never the model.
    text = _NOISE.sub(" ", str(text or "").replace("\xa0", " "))
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sku_key(text):
    """Return one normalized SKU key, or None when the text is not exactly one known SKU."""
    s = _clean(text)
    low = s.lower()
    if "xeon" in low:
        rest = low.split("xeon", 1)[1]
        models = list(_INTEL_MODEL.finditer(rest))
        if len(models) != 1 or not re.search(r"\d", models[0]["num"]):
            return None
        m = models[0]
        if rest[: m.start()].strip() not in ("", "6", "scalable"):
            return None
        tier = (m["tier"] or "").lower()
        tier = {"w": "w-", "d": "d-", "e": "e-", "e3": "e3-", "e5": "e5-", "e7": "e7-"}.get(tier, tier + " " if tier else "")
        return "intel xeon " + tier + m["num"].upper() + (" " + m["ver"].lower() if m["ver"] else "")
    for family in ("epyc", "opteron"):
        if family in low:
            rest = low.split(family, 1)[1]
            models = list(_AMD_MODEL.finditer(rest))
            if len(models) != 1 or rest[: models[0].start()].strip():
                return None
            m = models[0]
            num, suffix = m["num"].upper(), (m["suffix"] or "").upper()
            attached = re.fullmatch(r"(\d{3,4})(SE|HE|EE)", num) if family == "opteron" else None
            if attached and not suffix:
                num, suffix = attached[1], attached[2]
            return "amd " + family + " " + num + (" " + suffix if suffix else "")
    return None
