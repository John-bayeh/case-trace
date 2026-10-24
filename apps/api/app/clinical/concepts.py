"""Small explicit alias vocabulary; related symptoms are not interchangeable."""

import re

ALIASES = {
    "cough": ("cough", "coughing"),
    "chest pain": ("chest pain",),
    "chest tightness": ("chest tightness",),
    "shortness of breath": ("shortness of breath", "dyspnea", "dyspnoea"),
    "fever": ("fever", "febrile"),
    "headache": ("headache", "headaches"),
    "nausea": ("nausea",),
    "rash": ("rash",),
    "pneumonia": ("pneumonia",),
    "asthma": ("asthma",),
}
PATTERNS = {
    concept: re.compile(r"\b(?:" + "|".join(map(re.escape, aliases)) + r")\b", re.I)
    for concept, aliases in ALIASES.items()
}


def mentions(text: str) -> list[tuple[str, re.Match[str]]]:
    return sorted(
        [
            (concept, match)
            for concept, pattern in PATTERNS.items()
            for match in pattern.finditer(text)
        ],
        key=lambda item: item[1].start(),
    )
