import numpy as np
from scipy.stats import norm

def compute_statistics(real_mean, perm_means):
    """
    Statistiques sur le rang moyen (1→10).
    - p_lt = P(perm <= réel)
    - p_gt = 1 - p_lt
    - pval_lt = Phi(z)
    - pval_gt = 1 - Phi(z)
    Toutes les valeurs sont arrondies à 3 décimales pour l'affichage.
    """
    arr = np.asarray(perm_means, dtype=float)
    mean_sim = float(np.mean(arr))
    std_sim = float(np.std(arr, ddof=0))

    if std_sim == 0.0:
        z = 0.0
    else:
        z = (real_mean - mean_sim) / std_sim

    # Empiriques (complémentarité stricte)
    p_lt = float(np.mean(arr <= real_mean))
    p_gt = 1.0 - p_lt

    # Théoriques (normale)
    pval_lt = float(norm.cdf(z))
    pval_gt = 1.0 - pval_lt

    # ⬇️ On renvoie les floats et on laisse l'IHM décider du format
    return {
        "effectif_reel": real_mean,
        "moyenne": mean_sim,
        "ecart_type": std_sim,
        "z_score": z,
        "p_gt": p_gt,
        "p_lt": p_lt,
        "pval_gt": pval_gt,
        "pval_lt": pval_lt
    }
