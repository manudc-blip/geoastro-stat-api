# positions_planetes.py
from dataclasses import dataclass
from typing import List, Optional, Any
import math
from datetime import datetime, timezone
import os
import swisseph as swe

# --- Seuils canoniques en degrés ---
DECL_T1 = 11 + 48/60      # 11.8°
DECL_T2 = 20 + 16/60      # 20.266666...
DECL_T3 = 23 + 45/60      # 23.75°

def sign_from_declination(decl_deg: float, lambda_deg: float) -> str:
    """
    Affecte un 'Signe' selon (δ, branche géométrique du cycle via λ), indépendant de la rétro.
    Règle demandée :
      - Nord montant  : Bélier (0..T1), Taureau (T1..T2), Gémeaux (T2..T3)
      - Nord descendant: Vierge (T1..0), Lion (T2..T1), Cancer (T3..T2)
      - Sud descendant : Balance (0..-T1), Scorpion (-T1..-T2), Sagittaire (-T2..-T3)
      - Sud montant   : Poissons (-T1..0), Verseau (-T2..-T1), Capricorne (-T3..-T2)
    Le sens 'montant/descendant' est déterminé par la branche δ(λ) avec λ supposé croissant
    (mouvement direct) : dir_up := sign(cos λ).
    Aux tournants (cos λ ≈ 0), on force: Nord → descendant ; Sud → montant.
    À δ = 0 pile, on force: dir_up ? Bélier : Balance.
    """
    # Branche géométrique via λ (en radians)
    lam = math.radians(lambda_deg % 360.0)
    c = math.cos(lam)
    eps = 1e-12

    if   c >  eps: dir_up = True        # δ augmente le long de λ
    elif c < -eps: dir_up = False       # δ diminue le long de λ
    else:
        # Aux solstices (cos λ ≈ 0) : tournant
        # Nord -> descend ; Sud -> monte
        dir_up = (decl_deg < 0)

    # Cas exact à l'équateur : tranche sur la branche
    if abs(decl_deg) < 1e-12:
        return "Bélier" if dir_up else "Balance"

    north = (decl_deg > 0.0)
    d = abs(decl_deg)

    # Bande 0: [0..T1[  |  Bande 1: [T1..T2[  |  Bande 2: [T2..∞[
    if d < DECL_T1:
        band = 0
    elif d < DECL_T2:
        band = 1
    else:
        band = 2  # inclut aussi au-delà de T3 (Lune en grande déclinaison)

    if north:
        if dir_up:         # Nord montant
            return ("Bélier", "Taureau", "Gémeaux")[band]
        else:              # Nord descendant
            return ("Vierge", "Lion", "Cancer")[band]
    else:
        if dir_up:         # Sud montant
            return ("Poissons", "Verseau", "Capricorne")[band]
        else:              # Sud descendant
            return ("Balance", "Scorpion", "Sagittaire")[band]

# --- Modules internes ---
from domitude_conditionaliste import calc_domitude_features  # angularité (domitude réelle)

# --- Chemin Swiss Ephemeris ---
EPHE_PATH = os.path.join(os.path.dirname(__file__), "Swisseph")
swe.set_ephe_path(EPHE_PATH)

# --- Mapping noms FR -> constantes Swiss ---
SWE_BY_NAME = {
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

# IMPORTANT : garder le même ordre que la domitude
PLANETS = ["Soleil", "Lune", "Mercure", "Vénus", "Mars",
           "Jupiter", "Saturne", "Uranus", "Neptune", "Pluton"]

SIGNS = ["Bélier", "Taureau", "Gémeaux", "Cancer", "Lion", "Vierge",
         "Balance", "Scorpion", "Sagittaire", "Capricorne", "Verseau", "Poissons"]

@dataclass
class PlanetState:
    name: str
    lambda_deg: float         # longitude écliptique (0..360)
    sign: str                 # nom du Signe (FR)
    decl_deg: float           # déclinaison (N+ / S-)
    decl_speed_deg_per_day: Optional[float]  # vitesse δ instantanée (°/j)
    is_angular: bool          # angulaire ? (domitude conditionaliste)
    angular_zone: Optional[str] = None       # AS/MC/DS/FC/Zone si dispo

def _lambda_to_sign(lmbda: float) -> str:
    idx = int(math.floor((lmbda % 360.0) / 30.0))
    return SIGNS[idx]

def _jdut_from_datetime(dt_utc: datetime) -> float:
    # JJ UT fractionnaire attendu par Swiss Ephemeris
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    )

def get_positions(dt: datetime,
                  lat_deg: float,
                  lon_deg: float,
                  alt_m: float = 0.0) -> List[PlanetState]:
    """
    Calcule pour chaque planète :
      - λ (longitude écliptique), Signe,
      - δ (déclinaison) et dδ/dt (°/jour),
      - angularité (via domitude conditionaliste).
    """
    # Normalise en UTC "aware", puis passe "naive UTC" à la domitude si besoin
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)

    # 1) Angularité/zone par domitude (une passe pour toutes les planètes)
    #    calc_domitude_features attend un datetime naïf UTC dans ton code
    dom_feats = calc_domitude_features(dt_utc.replace(tzinfo=None), lat_deg, lon_deg)
    # Exemple structure: {"planete":"Soleil","est_angulaire":True,"zone_16":"Zone X",...}
    ang_by_name = {r["planete"]: (bool(r.get("est_angulaire")), r.get("zone_16")) for r in dom_feats}

    # 2) Positions astro via Swiss Ephemeris
    jd_ut = _jdut_from_datetime(dt_utc)
    results: List[PlanetState] = []

    FLG_ECL = swe.FLG_SWIEPH | swe.FLG_SPEED                    # écliptique + vitesses
    FLG_EQ  = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_EQUATORIAL  # équatorial + vitesses

    for name in PLANETS:
        ipl = SWE_BY_NAME[name]

        # 2a) Longitude écliptique (pour le Signe)
        pos_ecl, _ = swe.calc_ut(jd_ut, ipl, FLG_ECL)
        lambda_deg = float(pos_ecl[0]) % 360.0

        # 2b) Déclinaison + vitesse instantanée (°/jour)
        pos_eq, _ = swe.calc_ut(jd_ut, ipl, FLG_EQ)
        decl_deg = float(pos_eq[1])
        decl_speed_deg_per_day = float(pos_eq[4])  # dδ/dt

        # APRÈS : sens fixé par la branche géométrique via λ
        sign = sign_from_declination(decl_deg, lambda_deg)

        # 3) Angularité/zone depuis la domitude
        is_ang, zone = ang_by_name.get(name, (False, None))

        results.append(PlanetState(
            name=name,
            lambda_deg=lambda_deg,
            sign=sign,
            decl_deg=decl_deg,
            decl_speed_deg_per_day=decl_speed_deg_per_day,
            is_angular=is_ang,
            angular_zone=zone if is_ang else None
        ))

    return results

def as_table(positions: List[PlanetState], with_decl: bool = True, with_speed: bool = True) -> List[List[Any]]:
    """
    Table prête à imprimer (en-têtes + lignes) pour la CLI.
    """
    headers = ["Planète", "λ (°)", "Signe"]
    if with_decl:
        headers.append("δ (°)")
    if with_speed:
        headers.append("dδ/dt (°/j)")
    headers += ["Angulaire", "Zone"]

    rows: List[List[Any]] = [headers]
    for p in positions:
        row = [p.name, f"{p.lambda_deg:.2f}", p.sign]
        if with_decl:
            row.append(f"{p.decl_deg:.2f}")
        if with_speed:
            row.append("" if p.decl_speed_deg_per_day is None else f"{p.decl_speed_deg_per_day:.4f}")
        row += ["Oui" if p.is_angular else "Non", (p.angular_zone or "")]
        rows.append(row)
    return rows
