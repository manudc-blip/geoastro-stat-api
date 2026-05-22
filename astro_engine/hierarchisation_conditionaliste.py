
"""
Hiérarchisation conditionaliste (PLANÈTES) — OSSATURE SEULEMENT
----------------------------------------------------------------
- Ne recalcule rien d'astro : consomme la domitude réelle (zone_16, axe, est_angulaire)
  depuis domitude_conditionaliste.calc_domitude_features(...)
- Consomme les aspects (types, orbes) depuis aspects_utils (ou logique équivalente)
- Implémente la méthodo fournie par l’utilisateur (aucun calcul ici : ONLY stubs)

Étapes couvertes par la méthodo (planètes) :
1) Thèmes AVEC planètes angulaires (zones 1..4)
   - Dominantes : planètes en zones 1,2,3,4 (ordre 1>2>3>4)
   - Départs : distance à l’axe, puis hiérarchie planétaire (Lune > Soleil > Mercure > Vénus > Mars > Jupiter > Saturne > Uranus > Neptune > Pluton)
   - Sous-dominantes : planètes en ASPECTS aux angulaires (ordre aspects: CONJ > OPP > SQR > TRI > SXT) + nombre d’aspects + hiérarchie planétaire
   - Non-dominantes : planètes sans aspects aux angulaires → classement par zones non-angulaires (ordre zones 5..12 puis 13..16) + hiérarchie planétaire

2) Thèmes SANS planètes angulaires
   - Amas : ≥ 3 planètes en conjonction (orbes par groupe), si plusieurs amas → l’amas contenant la planète la plus RAPIDE est premier
   - Classement interne à chaque amas : hiérarchie planétaire
   - Sous-dominantes : planètes en aspects à/aux amas (mêmes règles que ci-dessus)
   - Non-dominantes : zones non-angulaires + hiérarchie planétaire
"""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Literal
from dataclasses import dataclass
from datetime import datetime

# ---------------------------------------------------------------------------
# 0) Constantes / Tables de référence (SANS pondérations numériques ici)
# ---------------------------------------------------------------------------

# Ordre de priorité des zones (1 = plus puissant). None = hors-zones
ZONE_PRIORITY: Dict[Optional[str], int] = {
    "Zone 1": 1, "Zone 2": 2, "Zone 3": 3, "Zone 4": 4,
    "Zone 5": 5, "Zone 6": 6, "Zone 7": 7, "Zone 8": 8,
    "Zone 9": 9, "Zone 10": 10, "Zone 11": 11, "Zone 12": 12,
    "Zone 13": 13, "Zone 14": 14, "Zone 15": 15, "Zone 16": 16,
    None: 99,
}

# Hiérarchie planétaire de départage (ex æquo)
PLANET_TIE_ORDER: List[str] = [
    "Lune", "Soleil", "Mercure", "Vénus", "Mars",
    "Jupiter", "Saturne", "Uranus", "Neptune", "Pluton"
]

# Hiérarchie des aspects (ordre méthodo : CONJ > OPP > SQR > TRI > SXT)
ASPECT_PRIORITY: Dict[Optional[str], int] = {
    "CONJ": 1, "OPP": 2, "SQR": 3, "TRI": 4, "SXT": 5, None: 99
}

# Rappel orbes conseillés par groupes (méthodo) — à appliquer dans aspects_utils
# Groupe 1: Lune, Soleil, Mercure, Vénus, Mars
# Groupe 2: Jupiter, Saturne, Uranus, Neptune, Pluton
ASPECT_ORBS_DEG = {
    "G1_G1": {"CONJ": 18.0, "OPP": 18.0, "SQR": 9.0,  "TRI": 9.0,  "SXT": 5.0},
    "G2_G2": {"CONJ": 14.0, "OPP": 14.0, "SQR": 7.0,  "TRI": 7.0,  "SXT": 3.0},
    "G1_G2": {"CONJ": 16.0, "OPP": 16.0, "SQR": 8.0,  "TRI": 8.0,  "SXT": 4.0},
}

GROUPE_1 = {"Lune", "Soleil", "Mercure", "Vénus", "Mars"}
GROUPE_2 = {"Jupiter", "Saturne", "Uranus", "Neptune", "Pluton"}

# Règle méthodo : “Les sextiles à partir de Saturne (inclus) ne sont pas pris en compte”
# → Concerne les sextiles où au moins une planète ∈ {Saturne, Uranus, Neptune, Pluton}
EXCLUDE_SEXTILES_FROM_SATURN_ON = True

ThemeType = Literal["avec_angulaires", "sans_angulaires"]


# ---------------------------------------------------------------------------
# 1) Types de données attendues en entrée
# ---------------------------------------------------------------------------

@dataclass
class PlanetFeat:
    nom: str
    domitude_deg: float
    maison: int                 # 1..12
    pos_maison_deg: float       # 0..30
    zone_16: Optional[str]      # "Zone 1".. "Zone 16" ou None
    zone_angulaire: Optional[str]   # "Zone 1".."Zone 4" si angulaire, sinon None
    axe: Optional[str]          # "AS"|"MC"|"DS"|"FC"|None
    est_angulaire: bool

@dataclass
class Aspect:
    p1: str
    p2: str
    type: str       # "CONJ"|"OPP"|"SQR"|"TRI"|"SXT"
    orb: float      # orbe en degrés (valeur positive)
    exact: bool = False


# ---------------------------------------------------------------------------
# 2) Construction du contexte (stubs)
# ---------------------------------------------------------------------------

def build_context(date_naissance: datetime,
                  latitude_deg: float,
                  longitude_deg: float
                  ) -> Tuple[List[PlanetFeat], List[Aspect]]:
    """
    Agrège les entrées nécessaires :
      - domitude réelle via domitude_conditionaliste.calc_domitude_features(...)
        -> fournit zone_16 / zone_angulaire / axe / est_angulaire
      - aspects via aspects_utils (avec application des orbes par groupes)
        -> exclus : sextiles impliquant Saturne ou au-delà (si règle activée)
    RETURN: (planetes, aspects)
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 3) Détections structurelles (amas / vitesse / isolées) — stubs
# ---------------------------------------------------------------------------

def detect_amas(planetes: List[PlanetFeat],
                aspects: List[Aspect],
                seuil_conj_deg_by_group: Dict[str, float] = {
                    "G1_G1": ASPECT_ORBS_DEG["G1_G1"]["CONJ"],
                    "G2_G2": ASPECT_ORBS_DEG["G2_G2"]["CONJ"],
                    "G1_G2": ASPECT_ORBS_DEG["G1_G2"]["CONJ"],
                },
                taille_min: int = 3) -> List[List[str]]:
    """Méthodo : stub — non utilisé à cette étape."""
    raise NotImplementedError


def fastest_planet_in_group(group: List[str]) -> str:
    """Stub — non utilisé à cette étape."""
    raise NotImplementedError


def detect_isolees(planetes: List[PlanetFeat],
                   aspects: List[Aspect],
                   rayon_deg: float = 12.0) -> List[str]:
    """Stub — non utilisé à cette étape."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 4) Scores / classements (stubs, sauf ANGULARITÉ implémentée ci-dessous)
# ---------------------------------------------------------------------------

def score_angularite(planete: PlanetFeat) -> Tuple[int, Dict]:
    """Stub — non utilisé à cette étape."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# ⚙️ Étape 1 demandée : utilitaire distance + classement des dominantes
# ---------------------------------------------------------------------------
def _maison_pos_to_domitude_deg(maison: int, pos_maison_deg: float) -> float:
    """Convertit (maison 1..12, position 0..30) en domitude_deg (0..360).
    Convention (cf. domitude_conditionaliste.trouver_maison):
    - la maison X occupe [0°,30°), XI [30°,60°), XII [60°,90°), I [90°,120°), ...
    - les axes en domitude sont: MC=0°, AS=90°, FC=180°, DS=270°.
    """
    if not (1 <= int(maison) <= 12):
        raise ValueError("maison doit être dans 1..12")
    if not (0.0 <= float(pos_maison_deg) < 30.0):
        # On tolère 30.0 en le ramenant à 0.0 de la maison suivante
        if abs(float(pos_maison_deg) - 30.0) < 1e-9:
            pos = 0.0
            m = ((int(maison) % 12) + 1)  # maison suivante
            slot = ((m - 1) - 9) % 12
            return slot * 30.0 + pos
        raise ValueError("pos_maison_deg doit être dans [0,30)")
    slot = ((int(maison) - 1) - 9) % 12
    return slot * 30.0 + float(pos_maison_deg)


def distance_a_axe(maison: int, pos: float) -> Tuple[str, float]:
    """Renvoie (axe_proche, distance_deg) vers l'axe le plus proche en DOMITUDE.
    Axes considérés: AS, MC, DS, FC.
    La distance respecte la géométrie de la domitude (0°=MC, 90°=AS, 180°=FC, 270°=DS).
    """
    dom = _maison_pos_to_domitude_deg(maison, pos)
    axes = {"MC": 0.0, "AS": 90.0, "FC": 180.0, "DS": 270.0}

    def circ_dist(a: float, b: float) -> float:
        d = abs((a - b + 180.0) % 360.0 - 180.0)
        return d

    best_axe = None
    best_d = 1e9
    for axe, deg in axes.items():
        d = circ_dist(dom, deg)
        if d < best_d - 1e-9:
            best_axe, best_d = axe, d
    return best_axe, best_d


def _zone_to_int(zone_16: Optional[str]) -> Optional[int]:
    if not zone_16:
        return None
    try:
        return int(zone_16.strip().split()[1])
    except Exception:
        return None


def _planet_tie_key(nom: str) -> int:
    """Renvoie l'indice de départage pour la planète (plus petit = plus prioritaire)."""
    try:
        return PLANET_TIE_ORDER.index(nom)
    except ValueError:
        # inconnue -> en dernier
        return len(PLANET_TIE_ORDER) + 1


def trouver_dominantes_angularite(planetes_feats: List[Dict]) -> List[Dict]:
    """Filtre et classe les planètes *angulaires* (zones 1..4).
    Règles:
      a) filtre est_angulaire == True
      b) groupe par zone via zone_16
      c) ordre de zone: 1 > 2 > 3 > 4
      d) départage dans la même zone par:
         d1) distance croissante au plus proche axe,
         d2) puis ordre planétaire fixe (Lune > Soleil > Mercure > Vénus > Mars > Jupiter > Saturne > Uranus > Neptune > Pluton)

    Sortie: liste ordonnée de dicts:
       {"planete": str, "zone": "Zone 1|2|3|4", "axe_proche": "AS|MC|DS|FC", "distance_deg": float}
    """
    # a) filtrer angulaires
    angulaires = [p for p in planetes_feats if bool(p.get("est_angulaire"))]

    if not angulaires:
        return []

    enriched = []
    for p in angulaires:
        m = int(p.get("maison"))
        pos = float(p.get("pos_maison_deg"))
        axe, dist = distance_a_axe(m, pos)
        zone = p.get("zone_16") or p.get("zone_angulaire") or ""
        enriched.append({
            "planete": p.get("planete") or p.get("nom") or "?",
            "zone": zone,
            "axe_proche": axe,
            "distance_deg": float(dist),
            "_zone_int": _zone_to_int(zone),
            "_tie": _planet_tie_key(p.get("planete") or p.get("nom") or "?"),
        })

    # b/c/d) tri multi-clés
    enriched.sort(key=lambda r: (r["_zone_int"], r["distance_deg"], r["_tie"]))
    # nettoyer les clés internes
    for r in enriched:
        r.pop("_zone_int", None)
        r.pop("_tie", None)
    return enriched

# ---------------------------------------------------------------------------
# Sous-dominantes : planètes en aspects aux angulaires (règles utilisateur)
# ---------------------------------------------------------------------------
from collections import defaultdict
from typing import Iterable, Set, Tuple

_SLOW_FROM_SATURN = {"Saturne", "Uranus", "Neptune", "Pluton"}  # pour la règle sextiles

def _is_sextile_excluded(p1: str, p2: str, aspect_type: str) -> bool:
    """
    Règle : “Les sextiles à partir de Saturne (inclus) ne sont pas pris en compte.”
    → on ignore un SXT dès qu’il implique Saturne, Uranus, Neptune ou Pluton.
    """
    if aspect_type != "SXT":
        return False
    return (p1 in _SLOW_FROM_SATURN) or (p2 in _SLOW_FROM_SATURN)

def _zone_index(zone_16: str | None) -> int:
    """Renvoie l'indice de zone (1..16) ou 99 si inconnu."""
    if not zone_16:
        return 99
    try:
        return int(zone_16.split()[1])
    except Exception:
        return 99

def _angular_planets_ordered(planetes_feats: list[dict]) -> list[str]:
    """
    Renvoie la liste des planètes angulaires (zones 1..4) ordonnée selon:
    - zone croissante (1 → 4),
    - distance à l’axe croissante,
    - puis ordre planétaire fixe.
    On réutilise trouver_dominantes_angularite pour garantir la même logique.
    """
    doms = trouver_dominantes_angularite(planetes_feats)
    return [d["planete"] for d in doms]

def _planet_tie_key_name(nom: str) -> int:
    """Indice de départage pour la planète (plus petit = plus prioritaire)."""
    try:
        return PLANET_TIE_ORDER.index(nom)
    except ValueError:
        return len(PLANET_TIE_ORDER) + 1

def _build_aspect_counters_toward_angulaires(
    planetes_feats: list[dict],
    aspects: Iterable[dict | "Aspect"],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, set[str]]]]:
    """
    Compte, pour chaque planète NON angulaire, le nombre d'aspects vers au moins
    une planète angulaire, par type (CONJ/OPP/SQR/TRI/SXT), en respectant:
      - exclusion des sextiles impliquant {Saturne, Uranus, Neptune, Pluton}.
    Retourne:
      counts[planete][type] -> int
      targets[planete][type] -> set des angulaires touchés
    """
    # Ensemble des angulaires
    angulaires: Set[str] = {p["planete"] for p in planetes_feats if p.get("est_angulaire")}

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    targets: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    def as_tuple(a) -> tuple[str, str, str]:
        # Supporte à la fois un dict brut et le dataclass Aspect défini plus haut
        if isinstance(a, dict):
            return a["p1"], a["p2"], a["type"]
        else:
            return a.p1, a.p2, a.type

    for a in aspects:
        p1, p2, atype = as_tuple(a)
        # filtrage sextiles
        if _is_sextile_excluded(p1, p2, atype):
            continue

        # Vers angulaire ? On ne retient que les paires où EXACTEMENT un des deux est angulaire
        p1_ang = p1 in angulaires
        p2_ang = p2 in angulaires
        if p1_ang ^ p2_ang:
            non_angulaire = p2 if p1_ang else p1
            # on n’accumule pas de points pour une planète déjà angulaire (sous-dominantes = non-angulaires)
            if non_angulaire in angulaires:
                continue
            counts[non_angulaire][atype] += 1
            targets[non_angulaire][atype].add(p1 if p2 == non_angulaire else p2)

    return counts, targets

def trouver_sous_dominantes_aspects(
    planetes_feats: list[dict],
    aspects: Iterable[dict | "Aspect"],
) -> list[dict]:
    """
    Classement des planètes en ASPECTS aux ANGULAIRES (sous-dominantes), selon les règles :

    • Ordre des familles d’aspects : CONJ > OPP > SQR > TRI > SXT
    • Règle Sextiles : “à partir de Saturne (inclus)” exclus.
    • Pour un type donné, départage par :
        1) nombre d’aspects de ce type vers les angulaires (descendant),
        2) ex æquo → ordre planétaire fixe (Lune > Soleil > Mercure > Vénus > Mars > Jupiter > Saturne > Uranus > Neptune > Pluton).

    NB : Le libellé “dans l’ordre des planètes présentes en zone 1,2,3,4” est respecté
    via l’ordre des cibles (angulaires) que l’on collecte, mais le classement final
    repose bien sur le NOMBRE d’aspects par type (puis départage fixe).
    """
    aspect_order = ["CONJ", "OPP", "SQR", "TRI", "SXT"]

    # Compteurs (par planète non-angulaire → par type)
    counts, targets = _build_aspect_counters_toward_angulaires(planetes_feats, aspects)

    # Liste des angulaires triés comme pour les dominantes (utile pour présenter les cibles)
    angulaires_tries = _angular_planets_ordered(planetes_feats)
    rank_in_ang = {name: i for i, name in enumerate(angulaires_tries)}

    results: list[dict] = []
    for atype in aspect_order:
        # Candidats = planètes non-angulaires ayant au moins 1 aspect 'atype' vers les angulaires
        cand = []
        for planete, d in counts.items():
            n = d.get(atype, 0)
            if n > 0:
                # ordonner les cibles selon l’ordre des dominantes angulaires (zone1 → 4, etc.)
                cibles = sorted(targets[planete][atype], key=lambda x: rank_in_ang.get(x, 10**6))
                cand.append({
                    "planete": planete,
                    "aspect_type": atype,
                    "compte": n,
                    "cibles": cibles,
                })

        # tri : n d’aspects (desc) puis ordre planétaire fixe
        cand.sort(key=lambda r: (-r["compte"], _planet_tie_key_name(r["planete"])))
        results.extend(cand)

    return results

# =========================
# THÈMES SANS ANGULARITÉS
# =========================
from collections import defaultdict, deque
from typing import Iterable, Set

def _planet_name(p: dict) -> str:
    return p.get("planete") or p.get("nom") or "?"

def _planet_order_key(nom: str) -> int:
    try:
        return PLANET_TIE_ORDER.index(nom)
    except ValueError:
        return len(PLANET_TIE_ORDER) + 1

def _zone_num_or_99(zone_16: str | None) -> int:
    if not zone_16:
        return 99
    try:
        return int(zone_16.split()[1])
    except Exception:
        return 99

def detecter_amas(
    planetes_feats: list[dict],
    aspects: Iterable[dict | Aspect],
    taille_min: int = 3,
) -> list[list[str]]:
    """
    Un amas = composante connexe d'un graphe où les arêtes sont les CONJONCTIONS (orbes déjà gérées
    par aspects_utils). On retourne toutes les composantes de taille >= taille_min, triées avec
    en premier l’amas qui contient la planète la plus RAPIDE (Lune > ... > Pluton).
    """
    noms = {_planet_name(p) for p in planetes_feats}
    # graphe non orienté des conjonctions
    g: dict[str, set[str]] = {n: set() for n in noms}

    def as_tuple(a) -> tuple[str, str, str]:
        if isinstance(a, dict):
            return a["p1"], a["p2"], a["type"]
        else:
            return a.p1, a.p2, a.type

    for a in aspects:
        p1, p2, atype = as_tuple(a)
        if atype != "CONJ":
            continue
        if p1 in noms and p2 in noms:
            g[p1].add(p2)
            g[p2].add(p1)

    # composantes connexes par BFS/DFS
    vus: set[str] = set()
    amas: list[list[str]] = []
    for v in noms:
        if v in vus:
            continue
        if not g[v]:  # planète sans conjonction
            vus.add(v)
            continue
        comp: list[str] = []
        dq = deque([v])
        vus.add(v)
        while dq:
            u = dq.popleft()
            comp.append(u)
            for w in g[u]:
                if w not in vus:
                    vus.add(w)
                    dq.append(w)
        if len(comp) >= taille_min:
            comp.sort(key=_planet_order_key)  # ordre interne fixe
            amas.append(comp)

    if not amas:
        return []

    # tri des amas : celui qui contient la planète la plus rapide en premier
    def fastest_key(comp: list[str]) -> int:
        return min(_planet_order_key(x) for x in comp)

    amas.sort(key=lambda comp: (fastest_key(comp), -len(comp)))
    return amas

def trouver_dominantes_amas(planetes_feats: list[dict], amas: list[list[str]]) -> list[dict]:
    """
    Dominantes = planètes de l’amas prioritaire (le premier renvoyé par detecter_amas),
    classées selon l’ordre planétaire fixe. On forge des champs compatibles avec
    _flat_ranking: zone='Amas prioritaire', axe_proche='-', distance_deg=0.0
    """
    if not amas:
        return []
    prioritaire = sorted(amas[0], key=_planet_order_key)
    out: list[dict] = []
    for nom in prioritaire:
        out.append({
            "planete": nom,
            "zone": "Amas prioritaire",
            "axe_proche": "-",
            "distance_deg": 0.0
        })
    return out

def trouver_sous_dominantes_aspects_vers_cibles(
    planetes_feats: list[dict],
    aspects: Iterable[dict | Aspect],
    cibles: Set[str],
) -> list[dict]:
    """
    Même logique que trouver_sous_dominantes_aspects(...), mais les cibles sont arbitraires
    (ex: planètes de l’amas prioritaire).
    - Ordre des types: CONJ > OPP > SQR > TRI > SXT
    - Départage: nombre d’aspects (desc) puis hiérarchie planétaire
    - Exclut les sextiles impliquant {Saturne, Uranus, Neptune, Pluton}
    - N'inclut pas les planètes faisant partie des cibles (elles sont DOM)
    """
    aspect_order = ["CONJ", "OPP", "SQR", "TRI", "SXT"]
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    targets: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    noms = {_planet_name(p) for p in planetes_feats}

    def as_tuple(a) -> tuple[str, str, str]:
        if isinstance(a, dict):
            return a["p1"], a["p2"], a["type"]
        else:
            return a.p1, a.p2, a.type

    for a in aspects:
        p1, p2, atype = as_tuple(a)
        if atype not in aspect_order:
            continue
        if _is_sextile_excluded(p1, p2, atype):
            continue
        if p1 not in noms or p2 not in noms:
            continue
        # exactement une cible
        p1_cible = p1 in cibles
        p2_cible = p2 in cibles
        if p1_cible ^ p2_cible:
            non_cible = p2 if p1_cible else p1
            if non_cible in cibles:
                continue
            counts[non_cible][atype] += 1
            targets[non_cible][atype].add(p1 if non_cible == p2 else p2)

    # Ordre de présentation des cibles (DOM) = ordre planétaire fixe
    cible_order = {name: i for i, name in enumerate(sorted(cibles, key=_planet_order_key))}

    results: list[dict] = []
    for atype in aspect_order:
        cand: list[dict] = []
        for planete, d in counts.items():
            n = d.get(atype, 0)
            if n <= 0:
                continue
            cibs = sorted(targets[planete][atype], key=lambda nm: cible_order.get(nm, 10**6))
            cand.append({
                "planete": planete,
                "aspect_type": atype,
                "compte": n,
                "cibles": cibs,
            })
        cand.sort(key=lambda r: (-r["compte"], _planet_order_key(r["planete"])))
        results.extend(cand)

    return results

def hierarchiser_theme_sans_angulaires(
    planetes_feats: list[dict],
    aspects: Iterable[dict | Aspect],
) -> tuple[list[dict], list[dict], list[str], list[list[str]]]:
    """
    Renvoie (dominantes, sous_dom_raw, nd_planetes, amas_trouves)
    - dominantes: structure compatible _flat_ranking (zone='Amas prioritaire', ...)
    - sous_dom_raw: liste de dicts {planete, aspect_type, compte, cibles}
    - nd_planetes: noms des ND, déjà triés selon zone non-angulaire (5→16) puis ordre planétaire
    - amas_trouves: liste des amas (listes de noms), triés (prioritaire en tête)
    """
    amas = detecter_amas(planetes_feats, aspects, taille_min=3)
    if not amas:
        # cas limite: ND = toutes les planètes triées par zone 5→16 puis ordre planétaire
        nd = []
        for f in planetes_feats:
            name = _planet_name(f)
            z = _zone_num_or_99(f.get("zone_16"))
            bucket = 0 if 5 <= z <= 16 else 1
            nd.append((bucket, z, _planet_order_key(name), name))
        nd.sort()
        nd_sorted = [name for _, _, _, name in nd]
        return [], [], nd_sorted, []

    # dominantes = planètes de l'amas prioritaire
    dom = trouver_dominantes_amas(planetes_feats, amas)
    prioritaire_set = set(p["planete"] for p in dom)

    sous_dom = trouver_sous_dominantes_aspects_vers_cibles(planetes_feats, aspects, prioritaire_set)

    # ND = le reste (hors DOM et hors SUB), triés par zone (5→16) puis ordre planétaire
    deja = prioritaire_set | {r["planete"] for r in sous_dom}
    nd = []
    for f in planetes_feats:
        name = _planet_name(f)
        if name in deja:
            continue
        z = _zone_num_or_99(f.get("zone_16"))
        bucket = 0 if 5 <= z <= 16 else 1
        nd.append((bucket, z, _planet_order_key(name), name))
    nd.sort()
    nd_sorted = [name for _, _, _, name in nd]

    return dom, sous_dom, nd_sorted, amas

# ---------------------------------------------------------------------------
# 5) Orchestrateur principal — stubs
# ---------------------------------------------------------------------------

def hierarchiser(date_naissance: datetime,
             latitude_deg: float,
             longitude_deg: float) -> List[Dict]:
    """
    Pipeline complet (stubs, non utilisé ici).
    """
    raise NotImplementedError

# --- Hiérarchisation des MAISONS ---------------------------------------------

RAPIDES = {"Soleil", "Lune", "Mercure", "Vénus", "Mars"}

def hierarchiser_maisons(planet_ranks: dict[str, int], planet_to_house: dict[str, str]):
    """
    Classe les 12 Maisons selon la méthode hiérarchique.

    planet_ranks : dict {planète: rang 1..10} (hiérarchie planétaire)
    planet_to_house : dict {planète: "Maison I".."Maison XII"}

    Retour :
      house_ranks   : dict {"Maison I": rang 1..12}
      houses_detail : dict {"Maison I": {... infos ...}}
    """

    # Initialisation des Maisons
    maisons = [f"Maison {i}" for i in range(1, 13)]
    details = {
        m: {
            "points_total": 0,
            "somme_rangs": 0,
            "nb_planetes": 0,
            "nb_rapides": 0,
            "planetes": []
        }
        for m in maisons
    }

    # Pondération 10 → 1 selon rang planétaire
    for planete, rang in planet_ranks.items():
        maison = planet_to_house.get(planete)
        if maison not in details:
            continue
        points = max(1, 11 - rang)  # rang1=10 pts ... rang10=1 pt
        d = details[maison]
        d["points_total"] += points
        d["somme_rangs"] += rang
        d["nb_planetes"] += 1
        if planete in RAPIDES:
            d["nb_rapides"] += 1
        d["planetes"].append(planete)

    # Tri multi-critères
    canon_index = {m: i for i, m in enumerate(maisons)}
    items = list(details.items())
    items.sort(
        key=lambda kv: (
            -kv[1]["points_total"],   # critère 1
            kv[1]["somme_rangs"],     # critère 2
            -kv[1]["nb_planetes"],    # critère 3
            -kv[1]["nb_rapides"],     # critère 4
            canon_index[kv[0]],       # stabilité finale
        )
    )

    house_ranks = {name: i+1 for i, (name, _) in enumerate(items)}
    return house_ranks, details
