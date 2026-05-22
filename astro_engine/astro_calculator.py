# -*- coding: utf-8 -*-
"""
astro_calculator.py — GeoAstro (rang planétaire 1→10)
- Pour un individu :
  • calcule domitude (zones 1..16, maisons, angularités…)
  • compte signes/familles/RET + aspects « valorisés »
  • calcule le CLASSEMENT planétaire complet DOM → SUB → ND
    et retourne pour chaque planète un RANG 1..10 (1 = plus dominante)
- Conçu pour être utilisé par le moteur de permutations : on agrégera
  des RANGS (moyennes/sommes), pas des poids arbitraires.
"""

import datetime as dt
from functools import lru_cache
import swisseph as swe

from signs_hierarchy import rank_signs
from positions_planetes import PlanetState
from domitude_conditionaliste import calc_domitude_features
from aspects_utils import compute_aspects_equatorial, count_aspects_equatorial
from hierarchisation_conditionaliste import (
    trouver_dominantes_angularite,
    trouver_sous_dominantes_aspects,
    PLANET_TIE_ORDER,
)

# ---------------------------------------------------------------------
# Config éphémérides
# ---------------------------------------------------------------------
swe.set_ephe_path("Swisseph")

# ---------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------
MAISONS = [
    "Maison I", "Maison II", "Maison III", "Maison IV",
    "Maison V", "Maison VI", "Maison VII", "Maison VIII",
    "Maison IX", "Maison X", "Maison XI", "Maison XII",
]

PLANET_IDS = {
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

SIGNS_START = {
    k: i * 30
    for i, k in enumerate([
        "Bélier", "Taureau", "Gémeaux", "Cancer", "Lion", "Vierge",
        "Balance", "Scorpion", "Sagittaire", "Capricorne", "Verseau", "Poissons"
    ])
}

ASPECT_ORDER = ["CONJ", "OPP", "SQR", "TRI", "SXT"]

_RAPIDES = {"Lune", "Soleil", "Mercure", "Vénus", "Mars"}

# ---------------------------------------------------------------------
# Caches de bas niveau (positions, aspects, domitude)
# ---------------------------------------------------------------------
@lru_cache(maxsize=262144)
def _lon_ecl_cached(jd: float, pid: int) -> float:
    return float(swe.calc_ut(jd, pid)[0][0])

@lru_cache(maxsize=262144)
def _equ_with_speed_cached(jd: float, pid: int) -> tuple[float, float]:
    arr = swe.calc_ut(jd, pid, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL | swe.FLG_SPEED)[0]
    return float(arr[1]), float(arr[4])

@lru_cache(maxsize=131072)
def _domitude_cached(y: int, m: int, d: int, h: int, mi: int, lat: float, lon: float):
    birth_dt = dt.datetime(y, m, d, h, mi)
    return calc_domitude_features(birth_dt, lat, lon)

# ---------------------------------------------------------------------
# Helpers (tie-keys, zones, etc.)
# ---------------------------------------------------------------------
def _tie_key_planet(name: str) -> int:
    try:
        return PLANET_TIE_ORDER.index(name)
    except ValueError:
        return len(PLANET_TIE_ORDER) + 1

def _zone_num(zone_16: str | None) -> int:
    if not zone_16:
        return 99
    try:
        return int(str(zone_16).split()[1])
    except Exception:
        return 99

# ---------------------------------------------------------------------
# CLASSEMENT PLANÉTAIRE → rangs 1..10
# ---------------------------------------------------------------------
def _best_subdominant_per_planet(sous_dom_raw: list[dict]) -> dict[str, dict]:
    prio = {t: i for i, t in enumerate(ASPECT_ORDER)}
    best: dict[str, dict] = {}
    for row in sous_dom_raw:
        p = row["planete"]; t = row["aspect_type"]; n = row["compte"]
        cur = best.get(p)
        if cur is None:
            best[p] = row
        else:
            if prio[t] < prio[cur["aspect_type"]]:
                best[p] = row
            elif prio[t] == prio[cur["aspect_type"]]:
                if n > cur["compte"]:
                    best[p] = row
                elif n == cur["compte"] and _tie_key_planet(p) < _tie_key_planet(cur["planete"]):
                    best[p] = row
    return best

def _compute_planet_ranks(dom_feats: list[dict], aspects_list: list[dict]) -> dict[str, int]:
    # 1) Dominantes (zones 1..4 triées)
    doms = trouver_dominantes_angularite(dom_feats)
    flat: list[str] = [d["planete"] for d in doms]
    deja = set(flat)

    # 2) Sous-dominantes (vers angulaires) : meilleur type par planète
    sous_dom_raw = trouver_sous_dominantes_aspects(dom_feats, aspects_list)
    best_sub = _best_subdominant_per_planet(sous_dom_raw)
    prio = {t: i for i, t in enumerate(ASPECT_ORDER)}
    sub_list = list(best_sub.values())
    sub_list.sort(key=lambda r: (prio[r["aspect_type"]], -r["compte"], _tie_key_planet(r["planete"])))
    for r in sub_list:
        p = r["planete"]
        if p not in deja:
            flat.append(p); deja.add(p)

    # 3) Non-dominantes : zones puis ordre planétaire
    nd = []
    for f in dom_feats:
        p = f["planete"]
        if p in deja:
            continue
        z = _zone_num(f.get("zone_16"))
        bucket = 0 if 5 <= z <= 12 else (1 if 13 <= z <= 16 else 2)
        nd.append((bucket, z, _tie_key_planet(p), p))
    nd.sort()
    flat.extend([p for _, _, _, p in nd])

    # 4) Rangs 1..10 (+ sécurité)
    ranks = {p: i + 1 for i, p in enumerate(flat)}
    for p in PLANET_IDS.keys():
        ranks.setdefault(p, len(ranks) + 1)
    return ranks

# ---------------------------------------------------------------------
# HIÉRARCHISATION DES MAISONS (depuis rangs planétaires)
# ---------------------------------------------------------------------
def _compute_house_ranks(dom_feats: list[dict], planet_ranks: dict[str, int]) -> tuple[dict, dict]:
    """
    Retourne:
      - house_ranks: {"Maison X": rang 1..12}
      - houses_detail: métriques par maison
    Règles de tri :
      1) points_total DESC (points = 11 - rang_planète → 10..1)
      2) somme_rangs DESC (méthode : « total le plus élevé l’emporte »)
      3) nb_planetes DESC
      4) nb_rapides DESC
      5) ordre canonique I..XII (stabilité)
    """
    details: dict[str, dict] = {
        name: {"points_total": 0, "somme_rangs": 0, "nb_planetes": 0, "nb_rapides": 0, "planetes": []}
        for name in MAISONS
    }

    for row in dom_feats:
        nom = row.get("planete")
        m_index = int(row.get("maison", 0)) - 1
        if not (0 <= m_index < 12) or not nom:
            continue
        house_name = MAISONS[m_index]
        rang = int(planet_ranks.get(nom, 10))
        points = max(1, 11 - rang)  # rang1→10 pts ... rang10→1 pt

        d = details[house_name]
        d["points_total"] += points
        d["somme_rangs"] += rang
        d["nb_planetes"] += 1
        d["nb_rapides"] += 1 if nom in _RAPIDES else 0
        d["planetes"].append(nom)

    canon_index = {name: i for i, name in enumerate(MAISONS)}
    items = list(details.items())
    items.sort(key=lambda kv: (
        -kv[1]["points_total"],
        -kv[1]["somme_rangs"],   # DESC selon la méthode
        -kv[1]["nb_planetes"],
        -kv[1]["nb_rapides"],
        canon_index[kv[0]],
    ))
    house_ranks = {name: i + 1 for i, (name, _) in enumerate(items)}
    return house_ranks, details


# --- NOUVEAU : hiérarchisation des QUADRANTS (depuis houses_detail) ---
def _compute_quadrant_ranks(houses_detail: dict[str, dict]) -> tuple[dict, dict]:
    """
    Agrège les métriques des maisons par quadrant et retourne :
      - quadrant_ranks: {"Oriental diurne": 1..4, ...}
      - quadrants_detail: mêmes métriques agrégées + maisons sources
    Règle de tri (comme Maisons) :
      1) points_total DESC
      2) somme_rangs DESC
      3) nb_planetes DESC
      4) nb_rapides DESC
      5) ordre canonique Q1→Q4
    """
    QMAP = {
        "Oriental diurne":   ["Maison I", "Maison II", "Maison III"],
        "Occidental diurne": ["Maison IV", "Maison V", "Maison VI"],
        "Occidental nocturne":["Maison VII", "Maison VIII", "Maison IX"],
        "Oriental nocturne": ["Maison X", "Maison XI", "Maison XII"],
    }

    details_q = {}
    for qname, maisons in QMAP.items():
        pts = sum(houses_detail[m]["points_total"] for m in maisons)
        srg = sum(houses_detail[m]["somme_rangs"]   for m in maisons)
        npl = sum(houses_detail[m]["nb_planetes"]   for m in maisons)
        nra = sum(houses_detail[m]["nb_rapides"]    for m in maisons)
        pls = []
        for m in maisons:
            pls.extend(houses_detail[m]["planetes"])
        details_q[qname] = {
            "points_total": pts,
            "somme_rangs": srg,
            "nb_planetes": npl,
            "nb_rapides": nra,
            "planetes": pls,
            "maisons": maisons,
        }

    canon = {"Oriental diurne":0, "Occidental diurne":1, "Occidental nocturne":2, "Oriental nocturne":3}
    items = list(details_q.items())
    items.sort(key=lambda kv: (
        -kv[1]["points_total"],
        -kv[1]["somme_rangs"],
        -kv[1]["nb_planetes"],
        -kv[1]["nb_rapides"],
        canon[kv[0]],
    ))
    ranks = {name: i+1 for i, (name, _) in enumerate(items)}
    return ranks, details_q

def _compute_hemisphere_ranks(houses_detail: dict[str, dict]) -> tuple[dict, dict]:
    """
    Agrège les métriques des maisons par hémisphère et retourne :
      - hemisphere_ranks: {"Hémisphère oriental": 1..2, ...}
      - hemispheres_detail: mêmes métriques agrégées + maisons sources
    Règle de tri (comme Maisons/Quadrants) :
      1) points_total DESC
      2) somme_rangs DESC
      3) nb_planetes DESC
      4) nb_rapides DESC
      5) ordre canonique (Oriental>Occidental, Nocturne>Diurne)
    """
    HMAP = {
        "Hémisphère oriental":  ["Maison I", "Maison II", "Maison III", "Maison X", "Maison XI", "Maison XII"],
        "Hémisphère occidental":["Maison IV", "Maison V", "Maison VI", "Maison VII", "Maison VIII", "Maison IX"],
        "Hémisphère nocturne":  ["Maison I", "Maison II", "Maison III", "Maison IV", "Maison V", "Maison VI"],
        "Hémisphère diurne":    ["Maison VII", "Maison VIII", "Maison IX", "Maison X", "Maison XI", "Maison XII"],
    }

    details_h = {}
    for hname, maisons in HMAP.items():
        pts = sum(houses_detail[m]["points_total"] for m in maisons)
        srg = sum(houses_detail[m]["somme_rangs"]   for m in maisons)
        npl = sum(houses_detail[m]["nb_planetes"]   for m in maisons)
        nra = sum(houses_detail[m]["nb_rapides"]    for m in maisons)
        pls = []
        for m in maisons:
            pls.extend(houses_detail[m]["planetes"])
        details_h[hname] = {
            "points_total": pts,
            "somme_rangs": srg,
            "nb_planetes": npl,
            "nb_rapides": nra,
            "planetes": pls,
            "maisons": maisons,
        }

    canon = {
        "Hémisphère oriental":0,
        "Hémisphère occidental":1,
        "Hémisphère nocturne":2,
        "Hémisphère diurne":3,
    }
    items = list(details_h.items())
    items.sort(key=lambda kv: (
        -kv[1]["points_total"],
        -kv[1]["somme_rangs"],
        -kv[1]["nb_planetes"],
        -kv[1]["nb_rapides"],
        canon[kv[0]],
    ))
    ranks = {name: i+1 for i, (name, _) in enumerate(items)}
    return ranks, details_h

# --- NOUVEAU : hiérarchisation des AXES ANGULAIRES (depuis dom_list) ---
def _compute_angular_axis_ranks(dom_feats: list[dict], planet_ranks: dict[str, int]) -> tuple[dict, dict]:
    """
    Agrège par axes d'angularité (AS/MC/DS/FC) à partir de zone_16 :
      Zone 1 -> Ascendant
      Zone 2 -> Milieu-du-Ciel
      Zone 3 -> Descendant
      Zone 4 -> Fond-du-Ciel

    Retourne :
      - angular_axis_ranks: {"Ascendant": 1..4, ...}
      - angular_axes_detail: métriques agrégées (points_total, somme_rangs, nb_planetes, nb_rapides, planetes, zones)
    Règle de tri : points_total ↓, somme_rangs ↓, nb_planetes ↓, nb_rapides ↓, ordre canonique AS>MC>DS>FC.
    """
    Z2AXIS = {
        "Zone 1": "Ascendant",
        "Zone 2": "Milieu-du-Ciel",
        "Zone 3": "Descendant",
        "Zone 4": "Fond-du-Ciel",
    }

    details = {
        "Ascendant":        {"points_total": 0, "somme_rangs": 0, "nb_planetes": 0, "nb_rapides": 0, "planetes": [], "zones": []},
        "Milieu-du-Ciel":   {"points_total": 0, "somme_rangs": 0, "nb_planetes": 0, "nb_rapides": 0, "planetes": [], "zones": []},
        "Descendant":       {"points_total": 0, "somme_rangs": 0, "nb_planetes": 0, "nb_rapides": 0, "planetes": [], "zones": []},
        "Fond-du-Ciel":     {"points_total": 0, "somme_rangs": 0, "nb_planetes": 0, "nb_rapides": 0, "planetes": [], "zones": []},
    }

    for row in dom_feats:
        z = row.get("zone_16")
        axis = Z2AXIS.get(z)
        if not axis:
            continue  # ignore zones 5..16
        p = row.get("planete")
        if not p:
            continue
        rang = int(planet_ranks.get(p, 10))
        points = max(1, 11 - rang)

        d = details[axis]
        d["points_total"] += points
        d["somme_rangs"]  += rang
        d["nb_planetes"]  += 1
        d["nb_rapides"]   += 1 if p in _RAPIDES else 0
        d["planetes"].append(p)
        d["zones"].append(z)

    canon = {"Ascendant": 0, "Milieu-du-Ciel": 1, "Descendant": 2, "Fond-du-Ciel": 3}
    items = list(details.items())
    items.sort(key=lambda kv: (
        -kv[1]["points_total"],
        -kv[1]["somme_rangs"],
        -kv[1]["nb_planetes"],
        -kv[1]["nb_rapides"],
        canon[kv[0]],
    ))
    ranks = {name: i + 1 for i, (name, _) in enumerate(items)}
    return ranks, details

# ---------------------------------------------------------------------
# Utilitaires divers
# ---------------------------------------------------------------------
def parse_lat_lon(coord: str) -> float:
    coord = coord.strip().upper()
    if not coord:
        raise ValueError("Coordonnée vide")
    if coord[-1] in ("N", "S", "E", "W"):
        value = float(coord[:-1])
        if coord[-1] in ("S", "W"):
            value *= -1
        return value
    return float(coord)

def julian_day(ind: dict) -> float:
    date = dt.datetime(ind["year"], ind["month"], ind["day"], ind["hour"], ind["minute"])
    return swe.julday(date.year, date.month, date.day, date.hour + date.minute / 60.0)

# ---------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------
def compute_features(ind: dict) -> dict:
    """
    Entrée `ind` (dict) : name, day, month, year, hour, minute, latitude, longitude
    Retour : dict avec notamment :
        - "planet_ranks" {planète: rang 1..10}
        - "signs" {signe: valeur brute}
        - "sign_ranks" {signe: rang 1..12}
        - "house_ranks" {Maison: rang 1..12}
        - "houses_detail" {Maison: métriques}
    """
    # ---- Préparation / domitude ----
    try:
        lat = parse_lat_lon(ind["latitude"])
        lon = parse_lat_lon(ind["longitude"])
        jd = julian_day(ind)
        swe.set_topo(lon, lat, 0)

        dom_list = _domitude_cached(
            ind["year"], ind["month"], ind["day"], ind["hour"], ind["minute"], lat, lon
        )
        dom_by_name = {d["planete"]: d for d in dom_list}

    except Exception as e:
        print(f"❌ Erreur sur l'individu : {ind.get('name', 'Inconnu')} — {e}")
        raise

    # ---- Accumulateurs ----
    houses = {k: 0 for k in MAISONS}
    quadrants = {"Oriental diurne": 0, "Occidental diurne": 0, "Occidental nocturne": 0, "Oriental nocturne": 0}
    hemispheres = {"Hémisphère oriental": 0, "Hémisphère occidental": 0, "Hémisphère nocturne": 0, "Hémisphère diurne": 0}
    angular_zones = {f"Zone {i}": 0 for i in range(1, 17)}
    angular_planets = set()
    zodiac_signs = {k: 0 for k in SIGNS_START}
    ret = {k: 0 for k in ["R", "E", "T", "r", "e", "t", "P", "p"]}
    longitudes = {}

    # (optionnel) maisons Placidus pour usage futur (non utilisées ici)
    try:
        swe.houses(jd, lat, lon, b"P")
    except Exception as e:
        print(f"❌ Erreur calcul des maisons : {e}")

    # ---- Boucle planètes : positions + comptages bruts ----
    for name, pid in PLANET_IDS.items():
        try:
            plon = _lon_ecl_cached(jd, pid) % 360.0
            longitudes[name] = plon
        except Exception as e:
            print(f"❌ Erreur swe.calc_ut pour {name} — {e}")
            continue

        d = dom_by_name.get(name)
        if not d:
            print(f"❌ Domitude introuvable pour {name}")
            continue

        # Zones 1..16 + angulaires
        z16 = d.get("zone_16")
        if z16:
            angular_zones[z16] = angular_zones.get(z16, 0) + 1
        if d.get("est_angulaire"):
            angular_planets.add(name)

        # Maison (domitude)
        house_index = int(d["maison"]) - 1
        house_name = MAISONS[house_index]
        houses[house_name] += 1

        # Quadrants
        if house_name in ("Maison I", "Maison II", "Maison III"):
            quadrants["Oriental diurne"] += 1
        elif house_name in ("Maison IV", "Maison V", "Maison VI"):
            quadrants["Occidental diurne"] += 1
        elif house_name in ("Maison VII", "Maison VIII", "Maison IX"):
            quadrants["Occidental nocturne"] += 1
        else:
            quadrants["Oriental nocturne"] += 1

        # Hémisphères
        if house_name in ("Maison I", "Maison II", "Maison III", "Maison X", "Maison XI", "Maison XII"):
            hemispheres["Hémisphère oriental"] += 1
        else:
            hemispheres["Hémisphère occidental"] += 1
        if house_name in ("Maison I", "Maison II", "Maison III", "Maison IV", "Maison V", "Maison VI"):
            hemispheres["Hémisphère nocturne"] += 1
        else:
            hemispheres["Hémisphère diurne"] += 1

        # Signes (valeurs brutes)
        for sign_name, deg0 in SIGNS_START.items():
            if deg0 <= plon < deg0 + 30.0:
                zodiac_signs[sign_name] += 1
                break

        # RET (inchangé — compte brut)
        if name in ("Soleil", "Vénus", "Mercure"): ret["R"] += 1
        if name in ("Jupiter", "Mars", "Saturne"): ret["E"] += 1
        if name in ("Uranus", "Neptune", "Pluton"): ret["T"] += 1
        if name in ("Soleil", "Jupiter", "Uranus"): ret["r"] += 1
        if name in ("Vénus", "Mars", "Neptune"): ret["e"] += 1
        if name in ("Mercure", "Saturne", "Pluton"): ret["t"] += 1
        if name in ("Soleil", "Mars", "Pluton"): ret["P"] += 1
        if name == "Lune": ret["p"] += 1

    # ---- Aspects ÉQUATORIAUX (RA/δ) : liste + comptage « valorisé »
    aspects = compute_aspects_equatorial(
        dt.datetime(ind["year"], ind["month"], ind["day"], ind["hour"], ind["minute"])
    )
    scores_aspects = count_aspects_equatorial(aspects, angular_planets)

    # ---- Hiérarchisation planètes → RANGS 1..10 (avec aspects équatoriaux)
    planet_ranks = _compute_planet_ranks(dom_list, aspects)

    # ---- Hiérarchisation signes → RANGS 1..12 (via module externe)
    try:
        planets_for_ranking = []
        for name, pid in PLANET_IDS.items():
            plon = longitudes.get(name)
            if plon is None:
                continue
            sign = None
            for sign_name, deg0 in SIGNS_START.items():
                if deg0 <= plon < deg0 + 30.0:
                    sign = sign_name
                    break
            if sign is None:
                continue

            decl, decl_speed = _equ_with_speed_cached(jd, pid)
            is_ang = bool(dom_by_name.get(name, {}).get("est_angulaire", False))

            planets_for_ranking.append(PlanetState(
                name=name,
                sign=sign,
                is_angular=is_ang,
                lambda_deg=plon,
                decl_deg=decl,
                decl_speed_deg_per_day=decl_speed,
            ))

        # APRÈS
        ranked_signs = rank_signs(planets_for_ranking, planet_ranks)
        sign_ranks = {s: i for i, (s, data) in enumerate(ranked_signs, start=1)}
    except Exception as e:
        print(f"❌ Erreur calcul rangs signes : {e}")
        sign_ranks = {s: 12 for s in SIGNS_START.keys()}

    # ---- Familles zodiacales (classées par points de signes)
    def _build_family_ranks_from_ranked(ranked):
        sign_points = {s: d.get('points_total', 0) for s, d in ranked}
        sign_nplan  = {s: d.get('nb_planetes', 0)  for s, d in ranked}
        sign_nang   = {s: sum(1 for x in d.get('detail', []) if x.get('angulaire')) for s, d in ranked}

        REACTIONS = {
            "Force d'excitation": ["Bélier", "Gémeaux", "Lion", "Balance", "Sagittaire", "Verseau"],
            "Force d'inhibition": ["Taureau", "Cancer", "Vierge", "Scorpion", "Capricorne", "Poissons"],
        }
        MOBILITES = {
            "Vitesse d'excitation": ["Bélier", "Taureau", "Gémeaux"],
            "Lenteur d'excitation": ["Cancer", "Lion", "Vierge"],
            "Vitesse d'inhibition": ["Balance", "Scorpion", "Sagittaire"],
            "Lenteur d'inhibition": ["Capricorne", "Verseau", "Poissons"],
        }
        PHASES = {
            "Sens des Contraires": ["Bélier", "Vierge", "Balance", "Poissons"],
            "Sens des Dosages":    ["Taureau", "Lion", "Scorpion", "Verseau"],
            "Sens des Ensembles":  ["Gémeaux", "Cancer", "Sagittaire", "Capricorne"],
        }

        def _aggregate(fam_map):
            scores, npl, nang = {}, {}, {}
            for fam, signs in fam_map.items():
                scores[fam] = sum(sign_points.get(s, 0) for s in signs)
                npl[fam]    = sum(sign_nplan.get(s, 0)  for s in signs)
                nang[fam]   = sum(sign_nang.get(s, 0)   for s in signs)
            return scores, npl, nang

        def _ranks(scores, npl, nang, order):
            ord_idx = {name: i for i, name in enumerate(order)}
            items = list(scores.items())
            items.sort(key=lambda kv: (kv[1], npl.get(kv[0], 0), nang.get(kv[0], 0), -ord_idx[kv[0]]), reverse=True)
            return {name: i + 1 for i, (name, _) in enumerate(items)}

        scR, npR, naR = _aggregate(REACTIONS)
        scM, npM, naM = _aggregate(MOBILITES)
        scP, npP, naP = _aggregate(PHASES)

        ranks_reac  = _ranks(scR, npR, naR, ["Force d'excitation", "Force d'inhibition"])
        ranks_mobi  = _ranks(scM, npM, naM, ["Vitesse d'excitation", "Lenteur d'excitation", "Vitesse d'inhibition", "Lenteur d'inhibition"])
        ranks_phase = _ranks(scP, npP, naP, ["Sens des Contraires", "Sens des Dosages", "Sens des Ensembles"])
        return ranks_reac, ranks_mobi, ranks_phase

    if 'ranked_signs' in locals():
        ranks_reac, ranks_mobi, ranks_phase = _build_family_ranks_from_ranked(ranked_signs)
    else:
        ranks_reac  = {"Force d'excitation": 1, "Force d'inhibition": 2}
        ranks_mobi  = {"Vitesse d'excitation": 1, "Lenteur d'excitation": 2, "Vitesse d'inhibition": 3, "Lenteur d'inhibition": 4}
        ranks_phase = {"Sens des Contraires": 1, "Sens des Dosages": 2, "Sens des Ensembles": 3}

    # ---- Hiérarchisation des MAISONS → RANGS 1..12
    house_ranks, houses_detail = _compute_house_ranks(dom_list, planet_ranks)
    quadrant_ranks, quadrants_detail = _compute_quadrant_ranks(houses_detail)
    hemisphere_ranks, hemispheres_detail = _compute_hemisphere_ranks(houses_detail)
    angular_axis_ranks, angular_axes_detail = _compute_angular_axis_ranks(dom_list, planet_ranks)

    # ---- Retour ----
    return {
        "planet_ranks": planet_ranks,
        "hp_ranks": planet_ranks,  # alias pratique
        "ret": ret,
        "signs": zodiac_signs,
        "sign_ranks": sign_ranks,
        "families": {
            "Force d'excitation": sum(zodiac_signs[s] for s in ("Bélier", "Gémeaux", "Lion", "Balance", "Sagittaire", "Verseau")),
            "Force d'inhibition": sum(zodiac_signs[s] for s in ("Taureau", "Cancer", "Vierge", "Scorpion", "Capricorne", "Poissons")),
            "Vitesse d'excitation": sum(zodiac_signs[s] for s in ("Bélier", "Taureau", "Gémeaux")),
            "Lenteur d'excitation": sum(zodiac_signs[s] for s in ("Cancer", "Lion", "Vierge")),
            "Vitesse d'inhibition": sum(zodiac_signs[s] for s in ("Balance", "Scorpion", "Sagittaire")),
            "Lenteur d'inhibition": sum(zodiac_signs[s] for s in ("Capricorne", "Verseau", "Poissons")),
            "Sens des Contraires": sum(zodiac_signs[s] for s in ("Bélier", "Vierge", "Balance", "Poissons")),
            "Sens des Dosages": sum(zodiac_signs[s] for s in ("Taureau", "Lion", "Scorpion", "Verseau")),
            "Sens des Ensembles": sum(zodiac_signs[s] for s in ("Gémeaux", "Cancer", "Sagittaire", "Capricorne")),
        },
        "houses": houses,  # compte brut
        "quadrants": quadrants,
        "hemispheres": hemispheres,
        "angular_zones": angular_zones,
        "aspects": scores_aspects,
        "angular_planets": angular_planets,
        "zod_reactions_ranks": ranks_reac,      # 1..2
        "zod_mobilities_ranks": ranks_mobi,     # 1..4
        "zod_phases_ranks": ranks_phase,        # 1..3
        "house_ranks": house_ranks,             # 1..12 (méthode)
        "houses_detail": houses_detail,         # métriques pour debug/affichage
        "quadrant_ranks": quadrant_ranks,
        "quadrants_detail": quadrants_detail,
        "hemisphere_ranks": hemisphere_ranks,
        "hemispheres_detail": hemispheres_detail,
        "angular_axis_ranks": angular_axis_ranks,
        "angular_axes_detail": angular_axes_detail,
    }
