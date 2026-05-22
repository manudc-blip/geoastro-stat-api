# -*- coding: utf-8 -*-
"""
aspects_utils.py — Détection des aspects en THÈME ÉCLIPTIQUE avec orbes G1/G2.
- Calcule les aspects à partir des longitudes écliptiques géocentriques SwissEph.
- Orbes conformes à la méthodo (G1/G2/G1-G2).
- API publique principale : compute_aspects(dt_utc) -> list[dict]
- API secondaire (si tu as déjà les longitudes) : detect_aspects(longitudes)
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Tuple

# ---------------------- Définition des aspects ----------------------
ASPECTS = {
    "Conjonction": 0,
    "Opposition": 180,
    "Carré": 90,
    "Trigone": 120,
    "Sextile": 60
}

# Groupes de planètes (méthodo)
GROUPE_1 = {"Soleil", "Lune", "Mercure", "Vénus", "Mars"}
GROUPE_2 = {"Jupiter", "Saturne", "Uranus", "Neptune", "Pluton"}

# Orbes par groupe et type d'aspect (méthodo)
ORBES = {
    "Conjonction": {(1, 1): 18, (2, 2): 14, (1, 2): 16, (2, 1): 16},
    "Opposition":  {(1, 1): 18, (2, 2): 14, (1, 2): 16, (2, 1): 16},
    "Carré":        {(1, 1): 9,  (2, 2): 7,  (1, 2): 8,  (2, 1): 8},
    "Trigone":      {(1, 1): 9,  (2, 2): 7,  (1, 2): 8,  (2, 1): 8},
    "Sextile":      {(1, 1): 5,  (2, 2): 3,  (1, 2): 4,  (2, 1): 4},
}

def get_groupe(planet_name: str) -> int:
    if planet_name in GROUPE_1:
        return 1
    elif planet_name in GROUPE_2:
        return 2
    return 0

def angular_distance(deg1: float, deg2: float) -> float:
    delta = abs(deg1 - deg2) % 360
    return min(delta, 360 - delta)

# ---------------------- Normalisation & helpers ----------------------
ASPECT_PRIORITY_NORM = {"CONJ": 1, "OPP": 2, "SQR": 3, "TRI": 4, "SXT": 5}

_ASPECT_NAME_TO_CODE = {
    "Conjonction": "CONJ",
    "Opposition": "OPP",
    "Carré": "SQR",
    "Trigone": "TRI",
    "Sextile": "SXT",
}
_ASPECT_CODE_TO_NAME = {v: k for k, v in _ASPECT_NAME_TO_CODE.items()}

EXCLUDE_SEXTILES_FROM_SATURN_ON = True
_TRANS_SATURN = {"Saturne", "Uranus", "Neptune", "Pluton"}

def aspect_name_to_code(name: str) -> str:
    return _ASPECT_NAME_TO_CODE.get(name, name)

def aspect_code_to_name(code: str) -> str:
    return _ASPECT_CODE_TO_NAME.get(code, code)

def aspect_priority(aspect_code: str) -> int:
    return ASPECT_PRIORITY_NORM.get(aspect_code, 99)

# ---------------------- Détection à partir de longitudes ----------------------
def list_all_aspects(longitudes: Dict[str, float]) -> List[dict]:
    """
    Énumère toutes les paires planétaires formant un aspect selon ORBES/ASPECTS.
    Retourne une liste de dicts:
      {"p1":..., "p2":..., "type": "CONJ|OPP|SQR|TRI|SXT", "orb": float}
    """
    planets = list(longitudes.keys())
    out: List[dict] = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1, p2 = planets[i], planets[j]
            lon1, lon2 = longitudes[p1], longitudes[p2]
            gpair = (get_groupe(p1), get_groupe(p2))
            angle = angular_distance(lon1, lon2)

            for aspect_name, exact_angle in ASPECTS.items():
                orbe = ORBES[aspect_name].get(gpair, 0)
                if abs(angle - exact_angle) <= orbe:
                    out.append({
                        "p1": p1,
                        "p2": p2,
                        "type": _ASPECT_NAME_TO_CODE[aspect_name],
                        "orb": abs(angle - exact_angle)
                    })
    return out

def aspects_to_targets(source: str,
                       targets: set,
                       aspects_list: List[dict],
                       exclude_sextiles_from_saturn_on: bool = EXCLUDE_SEXTILES_FROM_SATURN_ON) -> List[dict]:
    """
    Sélectionne les aspects où 'source' est en lien avec une planète de 'targets'.
    Applique la règle 'pas de sextiles à partir de Saturne (inclus)' si activée.
    Retourne une liste filtrée d’aspects (dicts).
    """
    sel: List[dict] = []
    for a in aspects_list:
        if a["p1"] == source and a["p2"] in targets:
            p_src, p_dst = a["p1"], a["p2"]
        elif a["p2"] == source and a["p1"] in targets:
            p_src, p_dst = a["p2"], a["p1"]
        else:
            continue

        if exclude_sextiles_from_saturn_on and a["type"] == "SXT":
            if p_src in _TRANS_SATURN or p_dst in _TRANS_SATURN:
                continue

        sel.append(a)

    sel.sort(key=lambda x: ASPECT_PRIORITY_NORM.get(x["type"], 99))
    return sel

def detect_aspects(longitudes: Dict[str, float]) -> List[dict]:
    """
    Fondation neutre : retourne la liste des aspects valides avec orbe/priority,
    SANS faire de classement de planètes.
    """
    lst = list_all_aspects(longitudes)
    for a in lst:
        a["priority"] = aspect_priority(a["type"])
        a["name"] = aspect_code_to_name(a["type"])
    return lst

# ---------------------- Longitudes SwissEph + API unifiée ----------------------
try:
    import swisseph as swe  # pyswisseph
except Exception:
    swe = None  # géré à l'appel

_PLANET_IDS = None

def _norm360(x: float) -> float:
    return x % 360.0

def get_longitudes_ecliptiques(dt_utc: datetime) -> Dict[str, float]:
    """
    Longitudes écliptiques géocentriques (0..360) des 10 planètes pour dt_utc.
    Utilise Swiss Ephemeris (pyswisseph). Sert d'entrée à detect_aspects(...).
    """
    if swe is None:
        raise ImportError("pyswisseph est requis. Installe: pip install pyswisseph")

    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt_utc.astimezone(timezone.utc)

    jd_ut = swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
    )
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    global _PLANET_IDS
    if _PLANET_IDS is None:
        _PLANET_IDS = {
            "Soleil": swe.SUN,
            "Lune": swe.MOON,
            "Mercure": swe.MERCURY,
            "Vénus": swe.VENUS,
            "Mars": swe.MARS,
            "Jupiter": swe.JUPITER,
            "Saturne": swe.SATURN,
            "Uranus": swe.URANUS,
            "Neptune": swe.NEPTUNE,
            "Pluton": swe.PLUTO,
        }

    longs: Dict[str, float] = {}
    for name, pid in _PLANET_IDS.items():
        res = swe.calc_ut(jd_ut, pid, flags)
        # (xx, rflag) ou [lon, lat, dist, lon_speed, ...]
        if isinstance(res, tuple):
            xx = res[0]
            lon = float(xx[0])
        else:
            lon = float(res[0])
        longs[name] = _norm360(lon)
    return longs

def compute_aspects(dt_utc: datetime) -> List[dict]:
    """
    Calcule les aspects en THÈME ÉCLIPTIQUE avec les ORBES du module
    (G1/G2 comme dans ORBES) et renvoie la même structure que detect_aspects().
    """
    longs = get_longitudes_ecliptiques(dt_utc)
    return detect_aspects(longs)

def detect_valorized_aspects(longitudes: Dict[str, float],
                             angular_planets: set[str] | set = None) -> Dict[str, int]:
    """
    Retourne un compteur des aspects valorisés par type (FR):
      {"Conjonction": n, "Opposition": n, "Carré": n, "Trigone": n, "Sextile": n}
    - Si angular_planets non vide: on ne compte que les aspects où AU MOINS
      une des deux planètes est angulaire.
    - Exclut les sextiles impliquant {Saturne, Uranus, Neptune, Pluton}.
    """
    angular_planets = set(angular_planets or [])
    aspects = detect_aspects(longitudes)  # produit des entrées avec .type (code) et .name (FR)

    counts = {"Conjonction": 0, "Opposition": 0, "Carré": 0, "Trigone": 0, "Sextile": 0}

    for a in aspects:
        p1, p2 = a["p1"], a["p2"]
        code = a["type"]          # "CONJ"|"OPP"|"SQR"|"TRI"|"SXT"
        name = a["name"]          # FR: "Conjonction", etc.

        # Exclusion des sextiles à partir de Saturne (inclus)
        if code == "SXT" and EXCLUDE_SEXTILES_FROM_SATURN_ON:
            if p1 in _TRANS_SATURN or p2 in _TRANS_SATURN:
                continue

        if angular_planets:
            if (p1 in angular_planets) or (p2 in angular_planets):
                counts[name] += 1
        else:
            # Pas de planètes angulaires -> on compte tous les aspects
            counts[name] += 1

    return counts

# === ASPECTS EN SPHÈRE LOCALE (ÉQUATORIALE : RA/δ) ===================

def _deg(x):  # rad -> deg
    return x * 180.0 / math.pi

def _rad(x):  # deg -> rad
    return x * math.pi / 180.0

def _spherical_sep_deg(ra1_deg: float, dec1_deg: float, ra2_deg: float, dec2_deg: float) -> float:
    """Angle sphérique grand cercle entre (α1,δ1) et (α2,δ2), en degrés."""
    a1, d1 = _rad(ra1_deg), _rad(dec1_deg)
    a2, d2 = _rad(ra2_deg), _rad(dec2_deg)
    cosd = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(a1 - a2)
    cosd = max(-1.0, min(1.0, cosd))
    return _deg(math.acos(cosd))

def compute_aspects_equatorial(dt_naive) -> list[dict]:
    """
    Aspects en sphère locale basés sur l'angle sphérique (RA/δ), GEOCENTRIQUE.
    - dt_naive est traité comme 'UT naïf' (même convention que le reste du moteur).
    - Indépendant du lieu (lat/lon non requis).
    Sortie: [{p1,p2,type,orb,exact}], où 'type' est le CODE ("CONJ","OPP","SQR","TRI","SXT")
    et les orbes sont pris dans ORBES (FR) selon le couple de groupes G1/G2 existant.
    """
    if swe is None:
        raise ImportError("pyswisseph requis pour compute_aspects_equatorial")

    # Assure l'init du mapping planètes FR -> IDs SwissEph déjà utilisé plus haut
    global _PLANET_IDS
    if _PLANET_IDS is None:
        _PLANET_IDS = {
            "Soleil": swe.SUN, "Lune": swe.MOON, "Mercure": swe.MERCURY, "Vénus": swe.VENUS, "Mars": swe.MARS,
            "Jupiter": swe.JUPITER, "Saturne": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluton": swe.PLUTO,
        }

    jd_ut = swe.julday(dt_naive.year, dt_naive.month, dt_naive.day,
                       dt_naive.hour + dt_naive.minute/60.0 + dt_naive.second/3600.0)

    flags = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL  # RA/DEC géocentriques (true-of-date)

    # RA/Dec par planète (en degrés)
    ra = {}
    dec = {}
    for name, pid in _PLANET_IDS.items():
        xx = swe.calc_ut(jd_ut, pid, flags)[0]  # [lon=RA°, lat=Dec°, dist, lon_speed, lat_speed, ...]
        ra[name]  = float(xx[0])
        dec[name] = float(xx[1])

    planets = list(_PLANET_IDS.keys())
    out = []
    for i in range(len(planets)):
        for j in range(i+1, len(planets)):
            p1, p2 = planets[i], planets[j]
            d = _spherical_sep_deg(ra[p1], dec[p1], ra[p2], dec[p2])  # 0..180

            gpair = (get_groupe(p1), get_groupe(p2))  # (1|2, 1|2)

            # Teste contre les angles canoniques FR (ASPECTS) avec ORBES FR par G1/G2
            # Priorité: CONJ > OPP > SQR > TRI > SXT
            for name_fr, exact in (("Conjonction", 0), ("Opposition", 180),
                                   ("Carré", 90), ("Trigone", 120), ("Sextile", 60)):
                # règle: pas de sextiles à partir de Saturne (inclus)
                if name_fr == "Sextile" and (p1 in _TRANS_SATURN or p2 in _TRANS_SATURN):
                    continue
                orbe = ORBES[name_fr].get(gpair, 0)
                delta = abs(d - exact)
                if delta <= orbe:
                    out.append({
                        "p1": p1,
                        "p2": p2,
                        "type": _ASPECT_NAME_TO_CODE[name_fr],  # "CONJ"|"OPP"|...
                        "orb": delta,
                        "exact": d,
                    })
                    break  # un seul aspect retenu par paire
    return out

# === Comptage des aspects ÉQUATORIAUX (RA/δ) =========================

def count_aspects_equatorial(aspects_list: list[dict],
                             angular_planets: set[str] | set = None,
                             include_total: bool = True) -> dict:
    """
    Score 0/1/2 par aspect équatorial (RA/δ) en fonction de l'angularité :
      - 0 si aucune des planètes n'est angulaire (Z1..Z4)
      - 1 si exactement une planète est angulaire
      - 2 si les deux sont angulaires

    Retourne un dict par type FR {"Conjonction": Σpts, "Opposition": Σpts, ...}
    + éventuellement une clé "TOTAL" (somme de tous les types) si include_total=True.
    """
    angular_planets = set(angular_planets or [])
    # mapping code -> nom FR (doit déjà exister dans le fichier ; sinon garde ce fallback)
    try:
        name_of = aspect_code_to_name  # fonction existante
    except NameError:
        _ASPECT_CODE_TO_NAME = {"CONJ": "Conjonction", "OPP": "Opposition", "SQR": "Carré", "TRI": "Trigone", "SXT": "Sextile"}
        name_of = lambda code: _ASPECT_CODE_TO_NAME.get(code, code)

    scores = {"Conjonction": 0, "Opposition": 0, "Carré": 0, "Trigone": 0, "Sextile": 0}
    total = 0

    for a in aspects_list:
        p1, p2 = a["p1"], a["p2"]
        code   = a["type"]  # "CONJ"|"OPP"|"SQR"|"TRI"|"SXT"
        nameFR = name_of(code)

        pts = (1 if p1 in angular_planets else 0) + (1 if p2 in angular_planets else 0)
        if pts <= 0:
            continue  # aucun point si zéro angulaire

        scores[nameFR] += pts
        total += pts

    if include_total:
        scores["TOTAL"] = total
    return scores

