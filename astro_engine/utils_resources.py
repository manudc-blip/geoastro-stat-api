from pathlib import Path

def module_dir(path: str) -> Path:
    return Path(path).resolve().parent

def resource_path(name: str, module_file: str) -> str:
    """
    Cherche une ressource :
    1) dans le dossier du module appelant
    2) dans le dossier racine GéoAstro
    """
    base = module_dir(module_file)
    candidates = [
        base / name,          # ex. Courbes/icon_save.png
        base.parent / name,   # ex. GéoAstro/icon_save.png
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(candidates[0])
