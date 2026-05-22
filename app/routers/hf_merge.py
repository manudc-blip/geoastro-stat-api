from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from urllib.parse import quote
import tempfile
import os
import io

from geoastro_hf_merge import merge_hf, read_source_csv

router = APIRouter()


@router.post("/hf-merge")
async def hf_merge(
    male_file: UploadFile = File(...),
    female_file: UploadFile = File(...),
):
    male_path = None
    female_path = None
    output_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_m:
            tmp_m.write(await male_file.read())
            male_path = tmp_m.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_f:
            tmp_f.write(await female_file.read())
            female_path = tmp_f.name

        male_source = read_source_csv(male_path)
        female_source = read_source_csv(female_path)

        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        output_path = output_file.name
        output_file.close()

        merge_hf(male_path, female_path, output_path)

        with open(output_path, "rb") as f:
            content = f.read()

        summary = [
            f"Langue détectée (H) : {male_source.lang.lang}",
            f"Colonnes H : {', '.join(male_source.headers)}",
            f"Colonnes F : {', '.join(female_source.headers)}",
            f"Éléments H : {len(male_source.rows)}",
            f"Éléments F : {len(female_source.rows)}",
            f"Union H/F : {len(set(male_source.rows.keys()) | set(female_source.rows.keys()))}",
            "",
            "CSV H/F généré avec succès.",
        ]

        headers = {
            "Content-Disposition": 'attachment; filename="merged_hf.csv"',
            "X-HF-Summary": quote(" | ".join(summary)),
        }

        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers=headers,
        )

    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500,
        )

    finally:
        for path in [male_path, female_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass