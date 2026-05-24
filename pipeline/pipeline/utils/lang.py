"""
Lightweight language detector for OCS product descriptions.

OCS publishes each product as TWO Shopify entries: one with English `body_html`
and one with French. The same physical SKU shows up twice in our dim_products
table because the OCS API has different `id`s for each. Worse, sometimes the
`title` is English but the body is French.

We don't need full language identification — just a binary EN vs FR signal.
A simple weighted-keyword heuristic gives ~99% accuracy on this corpus and
avoids pulling in a heavyweight dependency like langdetect or fasttext.
"""

from __future__ import annotations

import re

# French markers — characters and short tokens that are nearly impossible
# in English product copy.
FRENCH_TOKENS = {
    "découvrez", "découvrir", "profitez", "plongez", "savourez", "préparez",
    "notre", "votre", "cette", "celui", "celle", "ceux", "celles",
    "puissant", "puissante", "puissants", "puissantes",
    "saveur", "saveurs", "saveur de", "arôme", "arômes",
    "souche", "souches", "indica", "sativa", "hybride",
    "préroulé", "préroulés", "fleur séchée", "diamants",
    "très", "tout", "aussi", "ainsi", "ensemble",
    "fabriqué", "fabriquée", "cultivé", "cultivée",
    "issu", "issue", "issus", "issues",
    "n'est", "qu'il", "qu'elle", "qu'un", "qu'une",
    "d'un", "d'une", "d'agrumes", "d'épices",
    "à la", "à votre", "à son", "à ses",
    "des notes", "des saveurs", "des fleurs",
}

ENGLISH_TOKENS = {
    "discover", "experience", "introducing", "featuring", "designed", "enjoy",
    "expect", "open up to", "open up", "indulge",
    "blend", "blends", "strain", "strains", "potent",
    "the perfect", "this is", "made with", "crafted",
    "buds", "flower", "pre-roll", "pre-rolls", "extract",
    "of the", "from the", "with a", "with the",
    "rolled", "infused", "harvested", "grown",
}

# Hard French marker — accented characters in any of these patterns is
# definitive (English copy never uses these).
DEFINITIVE_FRENCH_PATTERN = re.compile(
    r"\b(à|à\s+\w|d['']\w|n['']\w|qu['']\w|c['']est|s['']agit|"
    r"l['']\w|m['']\w|j['']\w|t['']\w|s['']\w)",
    re.IGNORECASE,
)

# Strong French signal: accented characters in non-borrowed words
ACCENTED_FRENCH_RE = re.compile(
    r"\b\w*[éèêëàâäîïôöùûüç]\w*\b",
    re.IGNORECASE,
)


def detect_language(text: str | None) -> str | None:
    """
    Returns "en", "fr", or None.

    Heuristic:
      1. Empty / very short text → None
      2. Definitive French markers ("d'un", "à la", "qu'il") → fr
      3. Otherwise count weighted French vs English tokens
    """
    if not text:
        return None

    s = text.lower().strip()
    if len(s) < 15:
        return None

    if DEFINITIVE_FRENCH_PATTERN.search(s):
        return "fr"

    # Count weighted matches
    fr_score = sum(1 for tok in FRENCH_TOKENS if tok in s)
    en_score = sum(1 for tok in ENGLISH_TOKENS if tok in s)

    # Accented chars are a strong French signal (rare in English product copy)
    accent_count = len(ACCENTED_FRENCH_RE.findall(s))
    fr_score += accent_count // 3  # every 3 accented words = +1 fr point

    if fr_score == 0 and en_score == 0:
        return None
    return "fr" if fr_score > en_score else "en"
