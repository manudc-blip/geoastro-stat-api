from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from app.security import get_request_mode, ensure_trial_cohort_allowed

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2] / "cohorts"


@router.get("/cohorts/list")
def list_cohorts(
    lang: str = "fr",
    mode: str = "trial",
):
    current_mode = get_request_mode(mode)

    folder = BASE_DIR / lang

    if not folder.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    files = sorted([f.name for f in folder.glob("*.csv")])

    return {"files": files}

@router.get("/cohorts/download")
def download_cohort(
    lang: str,
    name: str,
    mode: str = "trial",
):
    current_mode = get_request_mode(mode)

    if current_mode == "trial":
        ensure_trial_cohort_allowed(lang, name)

    filepath = BASE_DIR / lang / name

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=filepath,
        filename=name,
        media_type="text/csv",
    )
