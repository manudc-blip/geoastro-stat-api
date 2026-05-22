import re
import pandas as pd

# Dictionnaire de correspondance FR <-> EN
COLUMN_EQUIV = {
    "Nom": "Nom", "Name": "Nom",
    "Jour": "Jour", "Day": "Jour",
    "Mois": "Mois", "Month": "Mois",
    "Année": "Année", "Year": "Année",
    "HeureTU": "HeureTU", "HourUT": "HeureTU",
    "MinuteTU": "MinuteTU", "MinuteUT": "MinuteTU",
    "Latitude": "Latitude",
    "Longitude": "Longitude",
}

def _normalize_coord(value: str, is_lon: bool) -> str:
    """
    Normalise une coordonnée saisie dans le CSV (FR/EN):
      - supprime espaces et symboles superflus (°, ', ")
      - remplace la virgule par un point
      - met en majuscules
      - accepte 'O' comme alias de 'W' (seulement pour longitude)
      - conserve le format 'nn.nnnX' attendu par le moteur (X ∈ {N,S,E,W})
    """
    s = str(value or "").strip()
    s = s.replace(",", ".")
    # enlever ° ' " et espaces
    s = re.sub(r"[°'\"\s]", "", s).upper()

    # Si l’utilisateur a mis le signe au lieu d’un hémisphère (ex: -2.35),
    # on laisse tel quel (le moteur sait gérer), sinon on s’assure d’avoir une lettre finale.
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return s  # ex: "-2.35" (OK)

    # cas '2.35O', '2.35E', etc.
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)([NSEWO])", s)
    if not m:
        raise ValueError(f"Coordonnée invalide: {value!r}")

    num, hemi = m.groups()
    if is_lon and hemi == "O":
        hemi = "W"   # alias FR pour Ouest
    return f"{num}{hemi}"

def load_data(filepath):
    df = pd.read_csv(filepath, sep=";")
    df = df.fillna("")

    # Renommer les colonnes selon la correspondance
    df.rename(columns={col: COLUMN_EQUIV.get(col, col) for col in df.columns}, inplace=True)

    # Vérifie que toutes les colonnes essentielles sont bien là
    required = ["Nom", "Jour", "Mois", "Année", "HeureTU", "MinuteTU", "Latitude", "Longitude"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Colonne obligatoire manquante : {col}")

    individuals = []
    for _, row in df.iterrows():
        # >>> Normalisation ici
        lat = _normalize_coord(row["Latitude"], is_lon=False)
        lon = _normalize_coord(row["Longitude"], is_lon=True)

        ind = {
            "name": row["Nom"],
            "day": int(row["Jour"]),
            "month": int(row["Mois"]),
            "year": int(row["Année"]),
            "hour": int(row["HeureTU"]),
            "minute": int(row["MinuteTU"]),
            "latitude": lat,     # ex: "48.53N" ou "-48.53"
            "longitude": lon,    # ex: "2.35W"  ou "-2.35"
        }
        individuals.append(ind)

    return individuals
