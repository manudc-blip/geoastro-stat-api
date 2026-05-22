import pandas as pd
from translations import CATEGORY_TRANSLATIONS


def export_results(results, filename: str = "resultats_geoastro.csv") -> None:
    """Export principal des résultats GéoAstro (version française).

    - Colonnes et intitulés identiques au tableau de l'onglet Analyse
    - Nombres formatés avec 2 décimales
    - Encodage UTF-8 avec BOM pour une ouverture correcte dans Excel
    """
    # Colonnes internes attendues dans `results`
    col_order = [
        "Catégorie",
        "effectif_reel",
        "moyenne",
        "ecart_type",
        "z_score",
        "p_gt",
        "p_lt",
        "pval_gt",
        "pval_lt",
    ]

    df = pd.DataFrame(results)

    # On garde uniquement les colonnes attendues, dans le bon ordre
    df = df[col_order]

    # Intitulés "grand public" utilisés dans l'IHM
    header_map_fr = {
        "Catégorie": "Catégorie astrologique",
        "effectif_reel": "Moyenne de l’échantillon",
        "moyenne": "Moyenne de la distribution",
        "ecart_type": "Écart-type",
        "z_score": "Z-score",
        "p_gt": "Proba empirique (surval)",
        "p_lt": "Proba empirique (sous-val)",
        "pval_gt": "P-value (surval)",
        "pval_lt": "P-value (sous-val)",
    }

    df = df.rename(columns=header_map_fr)

    # Export CSV : séparateur ';', 2 décimales, UTF-8 avec BOM
    df.to_csv(
        filename,
        sep=";",
        index=False,
        float_format="%.3f",
        encoding="utf-8-sig",
    )


def export_kde_distributions(
    kde_data,
    results,
    filename: str = "distributions_kde.csv",
    lang: str = "fr",
) -> None:
    """Export des distributions de permutations (KDE) pour chaque catégorie.

    Paramètres
    ----------
    kde_data : dict
        Dictionnaire {categorie_FR: [v0, v1, v2, ...]} tel que renvoyé par main.process().
    results : list[dict]
        Résultats agrégés (moyennes, écarts-types, z, p, p-values) pour chaque catégorie.
    filename : str
        Nom du fichier CSV de sortie.
    lang : {"fr", "en"}
        Langue des intitulés des colonnes et des catégories.
    """
    # Normaliser le code langue
    lang = (lang or "fr").lower()

    # Titres de colonnes selon la langue
    COLS_FR = {
        "effectif_reel": "effectif_reel",
        "moyenne": "moyenne",
        "ecart_type": "ecart_type",
        "z_score": "z_score",
        "p_gt": "p_gt",
        "p_lt": "p_lt",
        "pval_gt": "pval_gt",
        "pval_lt": "pval_lt",
        "index_name": "Catégorie",
    }
    COLS_EN = {
        "effectif_reel": "sample_mean",
        "moyenne": "distribution_mean",
        "ecart_type": "std_dev",
        "z_score": "z_score",
        "p_gt": "p_gt",
        "p_lt": "p_lt",
        "pval_gt": "pval_gt",
        "pval_lt": "pval_lt",
        "index_name": "Category",
    }
    COLS = COLS_EN if lang == "en" else COLS_FR

    # Indexer les stats par libellé de catégorie (toujours en FR dans `results`)
    stats_by_cat = {r.get("Catégorie"): r for r in results}

    rows = {}

    # Construire une ligne par catégorie présente dans kde_data
    for cat, values in (kde_data or {}).items():
        stats = stats_by_cat.get(cat, {})

        # Libellé final : traduit si EN, sinon FR d'origine
        emit_label = CATEGORY_TRANSLATIONS.get(cat, cat) if lang == "en" else cat

        row = {
            COLS["effectif_reel"]: stats.get("effectif_reel"),
            COLS["moyenne"]: stats.get("moyenne"),
            COLS["ecart_type"]: stats.get("ecart_type"),
            COLS["z_score"]: stats.get("z_score"),
            COLS["p_gt"]: stats.get("p_gt"),
            COLS["p_lt"]: stats.get("p_lt"),
            COLS["pval_gt"]: stats.get("pval_gt"),
            COLS["pval_lt"]: stats.get("pval_lt"),
        }

        # Échantillons (0, 1, 2, ...) tels quels
        for i, val in enumerate(values):
            row[str(i)] = val

        rows[emit_label] = row

    # DataFrame et export
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = COLS["index_name"]
    df.to_csv(filename, sep=";")
