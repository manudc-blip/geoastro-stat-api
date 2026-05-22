
def planet_score(planet_name):
    # retourne le rang 1..10 de la planète pour l’individu
    return lambda features: features.get("planet_ranks", {}).get(planet_name, 10)

def ret_score(ret_name):
    return lambda features: features.get("ret", {}).get(ret_name, 0)

def sign_score(sign_name):
    return lambda features: features.get("sign_ranks", {}).get(sign_name, 12)

def family_score(family_name):
    return lambda features: features.get("families", {}).get(family_name, 0)

def house_score(house_name):
    return lambda features: features.get("houses", {}).get(house_name, 0)

def quadrant_score(q_name):
    return lambda features: features.get("quadrants", {}).get(q_name, 0)

def hemisphere_score(h_name):
    return lambda features: features.get("hemispheres", {}).get(h_name, 0)

def angular_zone_score(zname):
    return lambda features: features.get("angular_zones", {}).get(zname, 0)

def aspect_score(aspect_name):
    return lambda features: features.get("aspects", {}).get(aspect_name, 0)

def zod_reaction_rank(fam_name):
    # Rang 1..2 dans la catégorie Réactions
    return lambda features: features.get("zod_reactions_ranks", {}).get(fam_name, 2)

def zod_mobility_rank(fam_name):
    # Rang 1..4 dans la catégorie Mobilités
    return lambda features: features.get("zod_mobilities_ranks", {}).get(fam_name, 4)

def zod_phase_rank(fam_name):
    # Rang 1..3 dans la catégorie Phases
    return lambda features: features.get("zod_phases_ranks", {}).get(fam_name, 3)

def house_rank(house_name):
    # Retourne le rang 1..12 de la Maison (1 = dominante)
    return lambda features: features.get("house_ranks", {}).get(house_name, 12)

def quadrant_rank(q_name):
    return lambda features: features.get("quadrant_ranks", {}).get(q_name, 4)

def hemisphere_rank(h_name):
    return lambda features: features.get("hemisphere_ranks", {}).get(h_name, 2)

def angular_axis_rank(axis_name):
    # Rang 1..4 pour Ascendant / MC / DS / FC
    return lambda features: features.get("angular_axis_ranks", {}).get(axis_name, 4)

def higher_is_better(category_name: str) -> bool:
    # Aspects = score (plus grand = mieux) ; le reste reste en "rangs" (plus petit = mieux)
    return category_name.startswith("Aspects")

# --- Familles RET : calcul du rang 1→8 par individu ---
from ret_familles import (
    hp_ranks_from_flat,
    compute_ret_ranking,
    normalize_planet_name,
)

PLANETS_CANON = ["soleil","lune","mercure","venus","mars","jupiter","saturne","uranus","neptune","pluton"]

def _extract_hp_ranks_from_features(features):
    """
    Récupère un dict {canon_planet: rang 1..10} à partir de features,
    en acceptant plusieurs formats possibles.
    """
    # 1) Dict prêt à l'emploi
    if "hp_ranks" in features and isinstance(features["hp_ranks"], dict):
        ranks = {}
        for k, v in features["hp_ranks"].items():
            ranks[normalize_planet_name(k)] = int(v)
        # vérification minimale
        if all(p in ranks for p in PLANETS_CANON):
            return ranks

    # 2) Liste à plat 1→10
    if "hp_flat" in features and isinstance(features["hp_flat"], (list, tuple)) and len(features["hp_flat"]) == 10:
        return hp_ranks_from_flat(features["hp_flat"])

    # 3) Fallback : clés individuelles genre "rank_Soleil" / "Soleil_rank"
    candidates = {}
    for key, val in features.items():
        low = key.lower()
        for p in ["soleil","lune","mercure","venus","mars","jupiter","saturne","uranus","neptune","pluton",
                  "sun","moon","mercury","venus","mars","jupiter","saturn","uranus","neptune","pluto"]:
            if p in low and ("rank" in low or "rang" in low):
                candidates[normalize_planet_name(p)] = int(val)
    if len(candidates) == 10 and all(p in candidates for p in PLANETS_CANON):
        return candidates

    raise KeyError("Impossible d’extraire les rangs HP depuis features (hp_flat ou hp_ranks manquant).")

def _make_ret_family_feature(family_code: str):
    """
    Retourne une fonction(feature_dict) -> rang 1..8 de la famille demandée pour CET individu.
    """
    def _fn(features):
        hp = _extract_hp_ranks_from_features(features)
        ret_order, _details = compute_ret_ranking(hp)
        # rang 1..8 (index + 1)
        return 1 + ret_order.index(family_code)
    return _fn

# Fonctions par famille
RET_FEATURES = {
    "Extensive Representation (R)": _make_ret_family_feature("R"),
    "Extensive Existence (E)": _make_ret_family_feature("E"),
    "Extensive Transcendence (T)": _make_ret_family_feature("T"),
    "Intensive representation (r)": _make_ret_family_feature("r"),
    "Intensive existence (e)": _make_ret_family_feature("e"),
    "Intensive transcendence (t)": _make_ret_family_feature("t"),
    "Extensive power (P)": _make_ret_family_feature("P"),
    "Intensive power (p)": _make_ret_family_feature("p"),
}

ALL_CATEGORIES = {
    # Planètes principales
    "Soleil": planet_score("Soleil"),
    "Lune": planet_score("Lune"),
    "Mercure": planet_score("Mercure"),
    "Vénus": planet_score("Vénus"),
    "Mars": planet_score("Mars"),
    "Jupiter": planet_score("Jupiter"),
    "Saturne": planet_score("Saturne"),
    "Uranus": planet_score("Uranus"),
    "Neptune": planet_score("Neptune"),
    "Pluton": planet_score("Pluton"),

    # Familles planétaires RET (rang 1→8)
    "Représentation extensive (R)": _make_ret_family_feature("R"),
    "Existence extensive (E)": _make_ret_family_feature("E"),
    "Transcendance extensive (T)": _make_ret_family_feature("T"),
    "représentation intensive (r)": _make_ret_family_feature("r"),
    "existence intensive (e)": _make_ret_family_feature("e"),
    "transcendance intensive (t)": _make_ret_family_feature("t"),
    "Pouvoir extensif (P)": _make_ret_family_feature("P"),
    "pouvoir intensif (p)": _make_ret_family_feature("p"),

    # Signes zodiacaux
    "Bélier": sign_score("Bélier"),
    "Taureau": sign_score("Taureau"),
    "Gémeaux": sign_score("Gémeaux"),
    "Cancer": sign_score("Cancer"),
    "Lion": sign_score("Lion"),
    "Vierge": sign_score("Vierge"),
    "Balance": sign_score("Balance"),
    "Scorpion": sign_score("Scorpion"),
    "Sagittaire": sign_score("Sagittaire"),
    "Capricorne": sign_score("Capricorne"),
    "Verseau": sign_score("Verseau"),
    "Poissons": sign_score("Poissons"),

    # Familles zodiacales
    "Force d'excitation": zod_reaction_rank("Force d'excitation"),
    "Force d'inhibition": zod_reaction_rank("Force d'inhibition"),
    "Vitesse d'excitation": zod_mobility_rank("Vitesse d'excitation"),
    "Lenteur d'excitation": zod_mobility_rank("Lenteur d'excitation"),
    "Vitesse d'inhibition": zod_mobility_rank("Vitesse d'inhibition"),
    "Lenteur d'inhibition": zod_mobility_rank("Lenteur d'inhibition"),
    "Sens des Contraires": zod_phase_rank("Sens des Contraires"),
    "Sens des Dosages":    zod_phase_rank("Sens des Dosages"),
    "Sens des Ensembles":  zod_phase_rank("Sens des Ensembles"),

    # Zones d'angularité → RANGS 1..4 (au lieu des scores bruts)
    "Ascendant": angular_axis_rank("Ascendant"),
    "Milieu-du-Ciel": angular_axis_rank("Milieu-du-Ciel"),
    "Descendant": angular_axis_rank("Descendant"),
    "Fond-du-Ciel": angular_axis_rank("Fond-du-Ciel"),

    # Maisons — RANGS 1..12
    "Maison I": house_rank("Maison I"),
    "Maison II": house_rank("Maison II"),
    "Maison III": house_rank("Maison III"),
    "Maison IV": house_rank("Maison IV"),
    "Maison V": house_rank("Maison V"),
    "Maison VI": house_rank("Maison VI"),
    "Maison VII": house_rank("Maison VII"),
    "Maison VIII": house_rank("Maison VIII"),
    "Maison IX": house_rank("Maison IX"),
    "Maison X": house_rank("Maison X"),
    "Maison XI": house_rank("Maison XI"),
    "Maison XII": house_rank("Maison XII"),

    # Quadrants → RANGS 1..4
    "Quadrant oriental diurne": quadrant_rank("Oriental diurne"),
    "Quadrant occidental diurne": quadrant_rank("Occidental diurne"),
    "Quadrant occidental nocturne": quadrant_rank("Occidental nocturne"),
    "Quadrant oriental nocturne": quadrant_rank("Oriental nocturne"),

    # Hémisphères → RANGS 1..2
    "Hémisphère oriental": hemisphere_rank("Hémisphère oriental"),
    "Hémisphère occidental": hemisphere_rank("Hémisphère occidental"),
    "Hémisphère diurne": hemisphere_rank("Hémisphère diurne"),
    "Hémisphère nocturne": hemisphere_rank("Hémisphère nocturne"),

    # Aspects planétaires
    "Conjonction": aspect_score("Conjonction"),
    "Opposition": aspect_score("Opposition"),
    "Carré": aspect_score("Carré"),
    "Trigone": aspect_score("Trigone"),
    "Sextile": aspect_score("Sextile"),
}

