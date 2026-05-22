import argparse
from datetime import datetime

# === Modules internes GeoAstro ===
from data_loader import load_data
from permutation_engine import generate_permutations
from astro_calculator import compute_features
from stat_analyzer import compute_statistics
from categories import ALL_CATEGORIES

from positions_planetes import get_positions, as_table as table_positions
from signs_hierarchy import rank_signs, as_table as table_ranking


# =====================================================
# PIPELINE PERMUTATIONS (analyse statistique sur CSV)
# =====================================================
def process(filepath, n=10000, progress_callback=None, lang="fr"):
    print(f">>> Début du traitement pour : {filepath}")
    individuals = load_data(filepath)
    print(f">>> {len(individuals)} individus chargés")

    if n < 1:
        raise ValueError("Le nombre de permutations doit être ≥ 1.")
    print(f">>> {n} permutations demandées")

    permutations = generate_permutations(individuals, num_permutations=n)
    print(f">>> {len(permutations)} permutations générées")

    N = len(individuals)
    if N == 0:
        raise ValueError("Aucun individu dans le fichier d’entrée.")

    categories_items = list(ALL_CATEGORIES.items())

    # progression
    step = 0
    if progress_callback:
        progress_callback(step)

    # === 1) Features réels ===
    print(">>> Calcul des features réels (1x)")
    real_features = [compute_features(ind) for ind in individuals]
    if progress_callback:
        step += 1
        progress_callback(step)

    real_means = {}
    for cat_name, feature_func in categories_items:
        s = sum(feature_func(feats) for feats in real_features)
        real_means[cat_name] = s / N

    # === 2) Features permutations ===
    print(">>> Calcul des features par permutation")
    perm_means_by_cat = {cat_name: [] for cat_name, _ in categories_items}

    for p_idx, perm_group in enumerate(permutations, start=1):
        perm_features = [compute_features(ind) for ind in perm_group]
        for cat_name, feature_func in categories_items:
            s = sum(feature_func(feats) for feats in perm_features)
            perm_means_by_cat[cat_name].append(s / N)

        if progress_callback:
            step += 1
            if (p_idx % 10 == 0) or (p_idx == n):
                progress_callback(step)

        if p_idx % 100 == 0:
            print(f"... {p_idx} permutations traitées")

    # === 3) Statistiques finales ===
    print(">>> Agrégation des statistiques par catégorie")
    results, kde_data = [], {}
    for cat_name, _ in categories_items:
        perm_means = perm_means_by_cat[cat_name]
        stats = compute_statistics(real_means[cat_name], perm_means)
        stats["Catégorie"] = cat_name
        results.append(stats)
        kde_data[cat_name] = perm_means

        if progress_callback:
            step += 1
            progress_callback(step)

    print(">>> Fin du traitement (export manuel via l'interface).")

    # ⚠️ Plus d’export KDE automatique : on remonte les données à l’IHM.
    return results, kde_data

# =====================================================
# OUTILS D’AFFICHAGE (tables en console)
# =====================================================
def print_table(table: list[list[str]]) -> None:
    widths = [max(len(str(row[i])) for row in table) for i in range(len(table[0]))]
    for r, row in enumerate(table):
        line = " | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row))
        print(line)
        if r == 0:
            print("-+-".join("-" * w for w in widths))


# =====================================================
# SOUS-COMMANDE : SIGNS (positions + hiérarchie Signes)
# =====================================================
def cli_signs(args: argparse.Namespace) -> None:
    # 1) Positions planétaires (affichage de contrôle)
    dt = datetime.fromisoformat(args.datetime)
    pos = get_positions(dt, lat_deg=args.lat, lon_deg=args.lon, alt_m=args.alt)

    tpos = table_positions(pos, with_decl=not args.no_decl, with_speed=args.speed)
    print("\nPositions planétaires :")
    print_table(tpos)

    # 2) Hiérarchie des Signes (avec +points de RANG)
    if args.rank:
        # --- CALCUL DES RANGS PLANÉTAIRES 1..10 POUR LA MÊME DATE/LIEU ---
        ind = {
            "name": "CLI",
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute,
            "latitude": str(args.lat),
            "longitude": str(args.lon),
        }
        features = compute_features(ind)                 # <- calcule la hiérarchie planétaire
        planet_ranks = features["planet_ranks"]         # dict {"Soleil": 1..10, ...}

        # --- CLASSEMENT DES SIGNES EN PASSANT LES RANGS ---
        ranked = rank_signs(pos, planet_ranks)          # <- plus de +0 !
        tr = table_ranking(ranked)
        print("\nPoints et classement des Signes :")
        print_table(tr)

    # 3) HIÉRARCHISATION DES MAISONS
    house_ranks = features.get("house_ranks", {})
    houses_detail = features.get("houses_detail", {})
    if house_ranks:
        print("\n=== Hiérarchisation des Maisons ===\n")
        table = [["Rang", "Maison", "Points", "SommeRangs", "NbPlanètes", "NbRapides", "Planètes"]]
        for maison, rang in sorted(house_ranks.items(), key=lambda kv: kv[1]):
            d = houses_detail[maison]
            table.append([
                str(rang),
                maison,
                str(d["points_total"]),
                str(d["somme_rangs"]),
                str(d["nb_planetes"]),
                str(d["nb_rapides"]),
                ", ".join(d["planetes"]),
            ])
        print_table(table)

    # 4) Aspects (sphère locale, domitude)
    from aspects_utils import compute_aspects_equatorial

    aspects = compute_aspects_equatorial(dt)
    if aspects:
        print("\n=== Aspects (sphère locale / domitude) ===")
        for a in sorted(aspects, key=lambda x: (x["type"], x["orb"])):
            p1, p2, t, orb = a["p1"], a["p2"], a["type"], a["orb"]
            exact = a.get("exact", None)
            if exact is not None:
                print(f"{p1:>7s} — {p2:<7s} | {t:>4s} | orbe = {orb:4.1f}° | écart exact = {exact:6.2f}°")
            else:
                print(f"{p1:>7s} — {p2:<7s} | {t:>4s} | orbe = {orb:4.1f}°")
    else:
        print("\n=== Aspects (sphère locale / domitude) ===\n(aucun aspect détecté)")

def build_arg_parser_signs(subparsers):
    p = subparsers.add_parser("signs", help="Positions planétaires + hiérarchisation des Signes")
    p.add_argument("--datetime", required=True,
                   help='Ex: "2025-08-14T12:00:00" ou "2025-08-14 12:00:00" (locale)')
    p.add_argument("--lat", type=float, required=True, help="Latitude en degrés (Nord +)")
    p.add_argument("--lon", type=float, required=True, help="Longitude en degrés (Est +)")
    p.add_argument("--alt", type=float, default=0.0, help="Altitude en mètres")
    p.add_argument("--no-decl", action="store_true", help="N’affiche pas la déclinaison")
    p.add_argument("--speed", action="store_true", help="Affiche la vitesse de déclinaison")
    p.add_argument("--rank", action="store_true",
                   help="Calcule et affiche les points par Signe + classement")
    p.set_defaults(func=cli_signs)

# =====================================================
# POINT D’ENTRÉE PRINCIPAL
# =====================================================
def main():
    parser = argparse.ArgumentParser(description="GéoAstro - Outils CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Ajout de la sous-commande signs
    build_arg_parser_signs(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
