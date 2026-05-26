from fastapi import APIRouter, UploadFile, File, Form
from app.services.stats_service import run_analysis
from fastapi import HTTPException
from app.security import get_request_mode, ensure_full_mode

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    n: int = Form(1000),
    lang: str = Form("fr"),
    mode: str = Form("trial"),
):
    current_mode = get_request_mode(mode)

    ensure_full_mode(current_mode)

    content = await file.read()

    result = run_analysis(
        content,
        n=n,
        lang=lang,
    )

    return result
