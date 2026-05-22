import math
import swisseph as swe
from datetime import datetime

def normaliser_radian(r):
    return r % (2 * math.pi)

def normaliser_degre(d):
    return d % 360

# === Constantes planètes et noms ===
planetes = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
            swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]
noms_planetes = ["Soleil", "Lune", "Mercure", "Vénus", "Mars",
                 "Jupiter", "Saturne", "Uranus", "Neptune", "Pluton"]

# === Zones de la sphère locale ===
zones_sphere_locale = {
    "MC+": (0, 18),
    "MC-": (-20, 0),
    "AS+": (90, 105),
    "AS-": (70, 90),
    "FC+": (180, 195),
    "FC-": (165, 180),
    "DS+": (270, 290),
    "DS-": (255, 270),
    # ... autres zones si besoin
}

# --- Fonctions de calcul ---
def calcul_domitude(ar_rad, decl_rad, tsn_rad, latitude_rad):
    sin_DA = math.tan(latitude_rad) * math.tan(decl_rad)
    sin_DA = max(min(sin_DA, 1), -1)
    DA = math.asin(sin_DA)
    SAD = math.pi / 2 + DA
    SAN = math.pi - SAD

    dm = ar_rad - tsn_rad
    if dm < 0:
        dm += 2 * math.pi

    if dm <= SAD:
        dm = dm * (math.pi / 2) / SAD
    elif dm > SAD and (dm - math.pi) >= SAN:
        dm = (dm - 2 * math.pi) * (math.pi / 2) / SAD
    elif dm > SAD and (dm - math.pi) < SAN and dm <= math.pi:
        dm = (dm - math.pi) * (math.pi / 2) / SAN + math.pi
    else:
        dm = (dm - math.pi) * (math.pi / 2) / SAN + math.pi

    return normaliser_degre(math.degrees(normaliser_radian(dm)))

def trouver_maison(dom_deg):
    slot = int(dom_deg // 30)        # 0..11 (0 = secteur autour du MC)
    maison = ((slot + 9) % 12) + 1   # 0->10 (X), 1->11 (XI), 2->12 (XII), 3->1 (I), ...
    pos = dom_deg % 30
    return maison, pos

# === Zones 1..16 (définition par maison + position 0..30°) ==================
# Règle d'évaluation : on teste dans l'ordre de priorité (1 → 16) et on
# renvoie la première zone qui matche. Ainsi, les zones angulaires (1..4)
# préemptent naturellement les zones non-angulaires (5..16).
#
# Hypothèses tirées du protocole :
# - "première moitié" = [0, 15), "deuxième moitié" = [15, 30)
# - "premier tiers" = [0, 10), "2 derniers tiers" = [10, 30)
# - "premiers 18°" = [0, 18), "12 premiers degrés" = [0, 12)
# NB : s'il existe des chevauchements (ex. Maison X), la priorité 1..4
# lève toute ambiguïté en pratique. Voir protocole utilisateur.  # 

def attribuer_zone_16(maison: int, pos_maison_deg: float) -> str:
    m = maison
    p = float(pos_maison_deg)

    # 1) ZONES ANGULAIRES (priorité maximale, bornes inclusives)
    # Zone 1 : 2 derniers tiers de XII (>=10°) OU 1re moitié de I (<=15°)
    if (m == 12 and p >= 10) or (m == 1 and p <= 15):
        return "Zone 1"

    # Zone 2 : 1ers 18° de X (<=18°) OU 2 derniers tiers de IX (>=10°)
    if (m == 10 and p <= 18) or (m == 9 and p >= 10):
        return "Zone 2"

    # Zone 3 : 2 premiers tiers de VII (<=20°) OU 2e moitié de VI (>=15°)
    if (m == 7 and p <= 20) or (m == 6 and p >= 15):
        return "Zone 3"

    # Zone 4 : 2e moitié de III (>=15°) OU 1re moitié de IV (<=15°)
    if (m == 3 and p >= 15) or (m == 4 and p <= 15):
        return "Zone 4"

    # 2) ZONES NON ANGULAIRES (autour des axes, bornes exclusives)
    # Zone 5 : 1er tiers de XII (<10°)
    if m == 12 and p < 10:
        return "Zone 5"

    # Zone 6 : 1er tiers de IX (<10°)
    if m == 9 and p < 10:
        return "Zone 6"

    # Zone 7 : 2e moitié de I (>15°)
    if m == 1 and p > 15:
        return "Zone 7"

    # Zone 8 : 12 derniers degrés de X (>18°)
    if m == 10 and p > 18:
        return "Zone 8"

    # Zone 9 : 10 derniers degrés de VII (>20°)
    if m == 7 and p > 20:
        return "Zone 9"

    # Zone 10 : 1re moitié de VI (<15°)
    if m == 6 and p < 15:
        return "Zone 10"

    # Zone 11 : 1re moitié de III (<15°)
    if m == 3 and p < 15:
        return "Zone 11"

    # Zone 12 : 2e moitié de IV (>15°)
    if m == 4 and p > 15:
        return "Zone 12"

    # 3) MAISONS ÉLOIGNÉES DES AXES (bornes exclusives aussi)
    if m == 11:
        return "Zone 13"
    if m == 8:
        return "Zone 14"
    if m == 2:
        return "Zone 15"
    if m == 5:
        return "Zone 16"

    # Sécurité
    return "Zone 16"

def is_angulaire(zone_16: str) -> bool:
    return zone_16 in {"Zone 1", "Zone 2", "Zone 3", "Zone 4"}

def identifier_zone(dom_deg):
    x = dom_deg % 360
    for nom_zone, (start, end) in zones_sphere_locale.items():
        s, e = start % 360, end % 360
        if s <= e:
            if s <= x < e:
                return nom_zone
        else:
            # intervalle qui traverse 360->0
            if x >= s or x < e:
                return nom_zone
    return None

def calc_domitude_features(date_naissance, latitude_deg, longitude_deg):
    """Retourne les données de domitude pour toutes les planètes"""
    jd_ut = swe.julday(date_naissance.year, date_naissance.month, date_naissance.day,
                       date_naissance.hour + date_naissance.minute / 60.0)
    lst_rad = math.radians(swe.sidtime(jd_ut) * 15 + longitude_deg)
    latitude_rad = math.radians(latitude_deg)

    out = []
    for i, p in enumerate(planetes):
        pos_eq, _ = swe.calc_ut(jd_ut, p, flags=swe.FLG_EQUATORIAL)
        ar_deg = pos_eq[0]
        decl_rad = math.radians(pos_eq[1])
        ar_rad = math.radians(ar_deg)
        dom_deg = calcul_domitude(ar_rad, decl_rad, lst_rad, latitude_rad)
        maison, pos = trouver_maison(dom_deg)
        zone = identifier_zone(dom_deg)

        # ➕ Nouveau : attribution de la zone 1..16 + statut angulaire
        zone16 = attribuer_zone_16(maison, pos)
        ang = is_angulaire(zone16)

        out.append({
            "planete": noms_planetes[i],
            "domitude_deg": dom_deg,
            "maison": maison,
            "pos_maison_deg": pos,
            "zone_locale": zone,
            "zone_16": zone16,
            "est_angulaire": ang,
            "zone_angulaire": zone16 if ang else None
        })

    return out

# --- Test manuel ---
if __name__ == "__main__":
    # Exemple : saisir des valeurs pour tester
    nom = input("Nom de la personne : ")
    date_str = input("Date/heure de naissance (YYYY-MM-DD HH:MM) UTC : ")
    lat = float(input("Latitude (°) : "))
    lon = float(input("Longitude (°) : "))
    date_naissance = datetime.strptime(date_str, "%Y-%m-%d %H:%M")

    print(f"--- {nom} ---")
    resultats = calc_domitude_features(date_naissance, lat, lon)
    for r in resultats:
        print(f"{r['planete']:<9} | Domitude: {r['domitude_deg']:7.2f}° | "
            f"Maison: {r['maison']} ({r['pos_maison_deg']:.2f}°) | "
            f"Zone 16: {r['zone_16']} | Angulaire: {r['est_angulaire']} | "
            f"Zone locale: {r['zone_locale']}")

