from fastapi import APIRouter, UploadFile, File, Form
from app.services.stats_service import run_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    n: int = Form(1000),
    lang: str = Form("fr"),
):
    content = await file.read()
    result = run_analysis(content, n=n, lang=lang)
    return result