import random

def generate_permutations(individuals, num_permutations=10000):
    """
    Mélange global des heures+minutes (HH:MM) en conservant les dates (YYYY-MM-DD),
    lat/lon et le reste des champs. Retourne une liste de groupes permutés
    (même API qu'avant), mais sans deepcopy du dataset complet.
    """
    all_permuted_groups = []

    # On extrait toutes les heures/minutes (en TU) une seule fois
    original_times = [(ind["hour"], ind["minute"]) for ind in individuals]

    for _ in range(num_permutations):
        # Tirage sans remise des HH:MM
        shuffled_times = random.sample(original_times, len(original_times))

        # On reconstruit un groupe "léger" sans deepcopy : nouveaux dicts avec champs nécessaires
        permuted_group = []
        for ind, (h, m) in zip(individuals, shuffled_times):
            permuted_group.append({
                "name": ind.get("name", ""),
                "day": ind["day"],
                "month": ind["month"],
                "year": ind["year"],
                "hour": h,
                "minute": m,
                "latitude": ind["latitude"],
                "longitude": ind["longitude"],
            })

        all_permuted_groups.append(permuted_group)

    return all_permuted_groups
