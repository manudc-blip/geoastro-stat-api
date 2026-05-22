# -*- coding: utf-8 -*-
"""
ret_familles.py — Classement des familles RET à partir des rangs HP (1→10) des planètes.

Règles :
- Pour les familles à 3 planètes (R, E, T, r, e, t, P) : on additionne les rangs HP des 3 planètes.
  Plus le total est petit, plus la famille est dominante.
- Cas particulier 'p' (Lune seule) : le rang HF de 'p' = rang HP de la Lune,
  avec cap à 8 si la Lune est 8/9/10 en HP. On insère 'p' à cette position
  dans le classement final (1→8).
- Départage en cas d’égalité de score entre familles à 3 planètes :
  ordre canonique: p, R, r, P, e, E, t, T (utilisé seulement pour les ex æquo entre familles à 3 planètes).
"""

from typing import Dict, List, Tuple, Any
import unicodedata

# ------------------------------------------------------------
# Normalisation des noms (FR/EN, accents, casse)
# ------------------------------------------------------------

def _strip_accents_lower(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower().strip()

# Canonical keys (internes) : "soleil","lune","mercure","venus","mars","jupiter","saturne","uranus","neptune","pluton"
_ALIAS_TO_CANON = {
    "soleil": "soleil", "sun": "soleil",
    "lune": "lune", "moon": "lune",
    "mercure": "mercure", "mercury": "mercure",
    "venus": "venus", "vénus": "venus", "venuse": "venus",
    "mars": "mars",
    "jupiter": "jupiter",
    "saturne": "saturne", "saturn": "saturne",
    "uranus": "uranus",
    "neptune": "neptune",
    "pluton": "pluton", "pluto": "pluton",
}

def normalize_planet_name(name: str) -> str:
    key = _strip_accents_lower(name)
    return _ALIAS_TO_CANON.get(key, key)

# ------------------------------------------------------------
# Définition des familles RET
# ------------------------------------------------------------

FAMILY_DEFS = {
    # Familles extensives
    "R": ("soleil", "venus", "mercure"),    # Représentation extensive
    "E": ("jupiter", "mars", "saturne"),    # Existence extensive
    "T": ("uranus", "neptune", "pluton"),   # Transcendance extensive
    # Familles intensives
    "r": ("soleil", "jupiter", "uranus"),   # représentation intensive
    "e": ("venus", "mars", "neptune"),      # existence intensive
    "t": ("mercure", "saturne", "pluton"),  # transcendance intensive
    # Pouvoir
    "P": ("soleil", "mars", "pluton"),      # Pouvoir extensif
    # "p" = Lune seule (gérée à part)
}

# Ordre canonique pour départager les ex æquo (familles à 3 planètes)
TIEBREAKER_ORDER = ["p", "R", "r", "P", "e", "E", "t", "T"]
_TIEBREAKER_INDEX = {fam: i for i, fam in enumerate(TIEBREAKER_ORDER)}

# ------------------------------------------------------------
# API principale
# ------------------------------------------------------------

def hp_ranks_from_flat(flat_hp_list: List[str]) -> Dict[str, int]:
    """Construit un dict de rangs HP à partir d'une liste ordonnée 1→10."""
    ranks: Dict[str, int] = {}
    for idx, pname in enumerate(flat_hp_list, start=1):
        ranks[normalize_planet_name(pname)] = idx
    return ranks

def _ensure_hp_ranks(hp_ranks: Dict[str, int]) -> Dict[str, int]:
    """Normalise les clés et valide la présence des 10 planètes."""
    canon: Dict[str, int] = {}
    for k, v in hp_ranks.items():
        canon[normalize_planet_name(k)] = int(v)
    required = {"soleil","lune","mercure","venus","mars","jupiter","saturne","uranus","neptune","pluton"}
    missing = [p for p in required if p not in canon]
    if missing:
        raise ValueError(f"hp_ranks incomplet, manquant(s) : {missing}")
    return canon

def compute_family_scores(hp_ranks: Dict[str, int]) -> Dict[str, int]:
    """Sommes des rangs HP pour R,E,T,r,e,t,P."""
    hp = _ensure_hp_ranks(hp_ranks)
    scores = {}
    for fam, members in FAMILY_DEFS.items():
        scores[fam] = sum(hp[m] for m in members)
    return scores

def compute_ret_ranking(hp_ranks: Dict[str, int]) -> Tuple[List[str], Dict[str, Any]]:
    """
    Retourne :
      - ret_order: liste ordonnée des 8 familles
      - details: dict (scores, rangs par planète, rang HP/HF Lune, etc.)
    """
    hp = _ensure_hp_ranks(hp_ranks)
    family_scores = compute_family_scores(hp)

    family_members_hp = {fam: {m: hp[m] for m in members} for fam, members in FAMILY_DEFS.items()}

    lune_hp_rank = hp["lune"]
    lune_hf_rank = lune_hp_rank if lune_hp_rank < 8 else 8

    fam_3 = list(FAMILY_DEFS.keys())  # ["R","E","T","r","e","t","P"]
    fam_3_sorted = sorted(fam_3, key=lambda f: (family_scores[f], _TIEBREAKER_INDEX.get(f, 999)))

    ret_order = list(fam_3_sorted)
    insert_pos = max(0, min(lune_hf_rank, 8) - 1)
    ret_order.insert(insert_pos, "p")

    details = {
        "family_scores": {**family_scores, "p": lune_hf_rank},
        "family_members_hp": family_members_hp,
        "lune_hp_rank": lune_hp_rank,
        "lune_hf_rank": lune_hf_rank,
    }
    return ret_order, details

def format_ret_ranking(ret_order: List[str], details: Dict[str, Any]) -> str:
    """Chaîne lisible 1→8 avec scores/membres."""
    lines = []
    lines.append("Classement RET (1→8) :")
    for i, fam in enumerate(ret_order, start=1):
        if fam == "p":
            lines.append(f"{i}) p — rang = {details['lune_hf_rank']} (HP Lune = {details['lune_hp_rank']})")
        else:
            score = details["family_scores"][fam]
            members = ", ".join(sorted(details["family_members_hp"][fam].keys()))
            lines.append(f"{i}) {fam} — score={score} — membres=({members})")
    return "\n".join(lines)
