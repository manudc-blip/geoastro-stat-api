# signs_hierarchy.py
from typing import Dict, List, Tuple
from positions_planetes import PlanetState  # uses fields: name, sign, is_angular, ...

SIGNS = ["Bélier","Taureau","Gémeaux","Cancer","Lion","Vierge",
         "Balance","Scorpion","Sagittaire","Capricorne","Verseau","Poissons"]

# Fixed points per planet (your new scheme, Pluton included)
PLANET_SIGN_POINTS: Dict[str, int] = {
    "Lune": 10,
    "Soleil": 9,
    "Mercure": 8,
    "Vénus": 7,
    "Mars": 6,
    "Jupiter": 5,
    "Saturne": 4,
    "Uranus": 3,
    "Neptune": 2,
    "Pluton": 1,
}

# Order used in tie-breaks (your rule 3)
TIE_BREAK_ORDER = ["Lune","Mercure","Vénus","Soleil","Mars","Jupiter","Saturne","Uranus","Neptune","Pluton"]
RAPIDES = {"Lune","Soleil","Mercure","Vénus"}

def _tie_tuple(sign: str, planets: List[PlanetState]) -> Tuple[int, ...]:
    """Counts planets in this sign following TIE_BREAK_ORDER (used for tie-breaking)."""
    return tuple(sum(1 for p in planets if p.sign == sign and p.name == nm) for nm in TIE_BREAK_ORDER)

def rank_signs(planets: List[PlanetState], planet_ranks: Dict[str, int] | None = None) -> List[Tuple[str, dict]]:
    """
    Returns a ranked list [(sign, data), ...] where data contains:
      - points_total
      - nb_planetes
      - nb_rapides
      - detail: [{planete, points_base, points_rang, points_total}]
    Scoring = PLANET_SIGN_POINTS[name] + (11 - rank)  if rank is provided (1..10), else just PLANET_SIGN_POINTS.
    """
    # init accumulators
    scores: Dict[str, dict] = {
        s: {"points_total": 0, "nb_planetes": 0, "nb_rapides": 0, "detail": []}
        for s in SIGNS
    }

    for p in planets:
        base = PLANET_SIGN_POINTS.get(p.name, 0)
        add_rank = 0
        if planet_ranks is not None:
            r = int(planet_ranks.get(p.name, 0))
            if 1 <= r <= 10:
                add_rank = 11 - r  # rank 1 -> +10, rank 10 -> +1

        total = base + add_rank
        s = p.sign
        d = scores[s]
        d["points_total"] += total
        d["nb_planetes"] += 1
        if p.name in RAPIDES:
            d["nb_rapides"] += 1
        d["detail"].append({
            "planete": p.name,
            "points_base": base,
            "points_rang": add_rank,
            "points_total": total,
        })

    # sorting key per your rules:
    def key_fn(item):
        sign, data = item
        return (
            data["points_total"],    # 1) total points
            data["nb_planetes"],     # 2) number of planets
            data["nb_rapides"],      # 3) number of fast planets
            _tie_tuple(sign, planets)  # 4) order Lune->...->Pluton
        )

    ranked = sorted(scores.items(), key=key_fn, reverse=True)
    return ranked

def as_table(ranked: list[tuple[str, dict]]) -> list[list[str]]:
    """
    Formate le classement des signes en tableau lisible.
    Chaque item de `ranked` doit être (signe, data) avec
    data = {
        "points_total": int,
        "nb_planetes": int,
        "nb_rapides": int,
        "detail": [
            {"planete": str, "points_base": int, "points_rang": int, "points_total": int},
            ...
        ]
    }
    """
    headers = ["Rang", "Signe", "Points", "Nb planètes", "Nb rapides", "Détail"]
    rows = [headers]
    for i, (sign, data) in enumerate(ranked, start=1):
        detail = ", ".join(
            f"{d['planete']}:{d['points_base']}+{d['points_rang']}={d['points_total']}"
            for d in data.get("detail", [])
        )
        rows.append([
            str(i),
            sign,
            str(data.get("points_total", 0)),
            str(data.get("nb_planetes", 0)),
            str(data.get("nb_rapides", 0)),
            detail
        ])
    return rows
