import os
import sys
import tempfile
import importlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENGINE_DIR = os.path.join(BASE_DIR, "astro_engine")

if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

geoastro_main = importlib.import_module("main")


def run_analysis(file_content: bytes, n: int = 1000, lang: str = "fr"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        results, kde_data = geoastro_main.process(
            tmp_path,
            n=n,
            progress_callback=None,
            lang=lang,
        )

        return {
            "status": "success",
            "permutations": n,
            "lang": lang,
            "results_count": len(results),
            "results": results,
            "kde_categories_count": len(kde_data),
            "kde_data": kde_data,
        }

    finally:
        os.remove(tmp_path)