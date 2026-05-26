from fastapi import HTTPException


TRIAL_ALLOWED_COHORTS = {
    "fr": "Médaillés Fields.csv",
    "en": "Fields medalists.csv",
}


def get_request_mode(mode: str | None) -> str:
    if mode == "full":
        raise HTTPException(
            status_code=403,
            detail="Mode complet non disponible sans authentification serveur.",
        )

    return "trial"


def ensure_trial_cohort_allowed(lang: str, filename: str):
    allowed = TRIAL_ALLOWED_COHORTS.get(lang)

    if filename != allowed:
        raise HTTPException(
            status_code=403,
            detail="Mode essai : cohorte non autorisée.",
        )


def ensure_full_mode(mode: str):
    if mode != "full":
        raise HTTPException(
            status_code=403,
            detail="Mode essai : fonctionnalité réservée à la version complète.",
        )
