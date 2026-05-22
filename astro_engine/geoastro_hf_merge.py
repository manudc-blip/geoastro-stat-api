# -*- coding: utf-8 -*-
"""
geoastro_hf_merge.py — Fusion H/F pour GéoAstro
Sortie = même forme que les CSV "résultats" de GéoAstro + colonne Groupe/Group.

- Lit deux CSV "sorties GéoAstro" (un Hommes, un Femmes)
- Détecte la langue (FR/EN) et la colonne libellé (Élément / Element /
  Catégorie astrologique / Category / Label / Name)
- Fait l'union des éléments H ∪ F (éléments manquants créés avec 0.0 sur les colonnes numériques)
- Conserve TOUTES les colonnes d'origine et leur ordre
- Ajoute une colonne "Groupe" (FR) / "Group" (EN) juste après la colonne libellé
- Normalisations demandées :
  * Angularités → interne AS/MC/DS/FC puis émission : FR AS/MC/DS/FC, EN ASC/MC/DSC/IC
  * Quadrants → ordre canon I→IV, ré-émission exacte FR/EN
  * Aspects → ne garder que Conj/Opp/Carré→Square/Trigone→Trine/Sextile
  * Maisons : I→XII (Maison/House)
  * Familles zodiacales : blocs F+,F- | V+,L+ | V-,L- | SC,SD,SE
  * Planètes/Signes : ordre naturel sinon ordre d’entrée
- Encodage : UTF-8 BOM ; séparateur `;`

CLI :
  python geoastro_hf_merge.py --h H.csv --f F.csv --out merged_hf.csv

UI :
  python geoastro_hf_merge.py   (sélecteurs de fichiers + résumé)
"""

from __future__ import annotations
import argparse, csv, io, os, sys
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

# ---------- Langues ----------
@dataclass
class LangSpec:
    lang: str
    group_col: str
    group_H: str
    group_F: str

FR = LangSpec("FR", "Groupe", "Hommes", "Femmes")
EN = LangSpec("EN", "Group", "Men", "Women")

FR_ASPECTS = ["Conjonction", "Opposition", "Carré", "Trigone", "Sextile"]
EN_ASPECTS = ["Conjunction", "Opposition", "Square", "Trine", "Sextile"]

ZOD_FAMILIES_BLOCKS = [["F+","F-"], ["V+","L+"], ["V-","L-"], ["SC","SD","SE"]]

PLANETS_ORDER_FR = ["Soleil","Lune","Mercure","Vénus","Mars","Jupiter","Saturne","Uranus","Neptune","Pluton"]
PLANETS_ORDER_EN = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]

SIGNS_ORDER_FR = ["Bélier","Taureau","Gémeaux","Cancer","Lion","Vierge","Balance","Scorpion","Sagittaire","Capricorne","Verseau","Poissons"]
SIGNS_ORDER_EN = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

HOUSES_PREFIX_FR = "Maison "
HOUSES_PREFIX_EN = "House "
ROMANS_1_12 = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]

QUADS_FR = [
    "Quadrant oriental diurne",
    "Quadrant occidental diurne",
    "Quadrant occidental nocturne",
    "Quadrant oriental nocturne",
]
QUADS_EN = [
    "Diurnal Eastern Quadrant",
    "Diurnal Western Quadrant",
    "Nocturnal Western Quadrant",
    "Nocturnal Eastern Quadrant",
]

# ---------- utilitaires I/O ----------
def sniff_delimiter(sample_bytes: bytes) -> str:
    try:
        s = sample_bytes.decode("utf-8-sig", errors="ignore")
    except Exception:
        s = sample_bytes.decode("latin-1", errors="ignore")
    try:
        return csv.Sniffer().sniff(s, delimiters=";,").delimiter
    except Exception:
        return ";"

def normalize_number(x: str) -> float:
    if x is None: return 0.0
    s = str(x).strip()
    if not s: return 0.0
    s = s.replace(",", ".")
    try: return float(s)
    except Exception: return 0.0

def detect_lang(headers: List[str], rows: List[dict]) -> LangSpec:
    low = " ".join((h or "").lower() for h in headers)
    if "élément" in low or "pourcentage" in low or "groupe" in low or "catégorie" in low or "categorie" in low:
        return FR
    return EN

def pick_label_column(headers: List[str]) -> Optional[str]:
    aliases = [
        "élément","element",
        "catégorie astrologique","categorie astrologique",
        "catégorie","categorie","category",
        "astrological category",
        "label","libellé","libelle","name","nom","item","feature"
    ]
    for h in headers:
        if (h or "").lower().strip() in aliases:
            return h
    return headers[0] if headers else None

def numeric_columns(headers: List[str], rows: List[dict]) -> List[str]:
    nums = []
    for h in headers:
        if not h: continue
        ok = tot = 0
        for r in rows[:80]:
            v = r.get(h)
            if v is None or str(v).strip()=="":
                continue
            tot += 1
            try:
                float(str(v).replace(",", "."))
                ok += 1
            except Exception:
                pass
        if tot>0 and ok/tot>=0.8:
            nums.append(h)
    return nums

# ---------- catégories & canons ----------
def is_house(label: str, lang: LangSpec) -> bool:
    pref = HOUSES_PREFIX_FR if lang is FR else HOUSES_PREFIX_EN
    return label.startswith(pref) and label[len(pref):].strip().upper() in ROMANS_1_12

def house_index(label: str, lang: LangSpec) -> int:
    pref = HOUSES_PREFIX_FR if lang is FR else HOUSES_PREFIX_EN
    rom = label[len(pref):].strip().upper()
    return ROMANS_1_12.index(rom) if rom in ROMANS_1_12 else 999

def is_planet(label: str, lang: LangSpec) -> bool:
    return label in (PLANETS_ORDER_FR if lang is FR else PLANETS_ORDER_EN)

def is_sign(label: str, lang: LangSpec) -> bool:
    return label in (SIGNS_ORDER_FR if lang is FR else SIGNS_ORDER_EN)

def is_aspect(label: str, lang: LangSpec) -> bool:
    return label in (FR_ASPECTS if lang is FR else EN_ASPECTS)

def is_quadrant_like(label: str, lang: LangSpec) -> bool:
    s = label.lower()
    return (("quadrant" in s) and
            (("oriental" in s or "occidental" in s or "eastern" in s or "western" in s)) and
            (("diurne" in s or "nocturne" in s or "diurnal" in s or "nocturnal" in s)))

def quadrant_internal(label: str, lang: LangSpec) -> Optional[int]:
    s = label.lower()
    if lang is FR:
        if "oriental" in s and "diurne" in s: return 0
        if "occidental" in s and "diurne" in s: return 1
        if "occidental" in s and "nocturne" in s: return 2
        if "oriental" in s and "nocturne" in s: return 3
    else:
        if "diurnal" in s and "eastern" in s: return 0
        if "diurnal" in s and "western" in s: return 1
        if "nocturnal" in s and "western" in s: return 2
        if "nocturnal" in s and "eastern" in s: return 3
    return None

def quadrant_emit(idx: int, lang: LangSpec) -> str:
    return QUADS_FR[idx] if lang is FR else QUADS_EN[idx]

import re

def angular_to_internal(label: str, lang: LangSpec) -> Optional[str]:
    s = label.strip()
    up = s.upper()

    # motifs sûrs, avec limites de mots
    if re.search(r"\bAS(C|CENDANT)?\b", up) or re.search(r"\bASCENDANT\b", up):
        return "AS"
    if re.search(r"\bMC\b|\bMIDHEAVEN\b|MILIEU[- ]DU[- ]CIEL", up):
        return "MC"
    if re.search(r"\bDS(C|CENDANT)?\b", up) or re.search(r"\bDESCENDANT\b", up):
        return "DS"
    if re.search(r"\b(FC|IC)\b|\bIMUM COELI\b|FOND[- ]DU[- ]CIEL", up):
        return "FC"
    return None

def angular_emit(code: str, lang: LangSpec) -> str:
    if lang is FR:
        # Noms complets en français
        return {
            "AS": "Ascendant",
            "MC": "Milieu-du-Ciel",
            "DS": "Descendant",
            "FC": "Fond-du-Ciel",
        }[code]
    else:
        # Noms complets en anglais
        return {
            "AS": "Ascendant",
            "MC": "Midheaven",
            "DS": "Descendant",
            "FC": "Imum Coeli",
        }[code]

def is_hemisphere_like(label: str, lang: LangSpec) -> bool:
    s = label.lower()
    return ("hémisphère" in s) if lang is FR else ("hemisphere" in s)

def is_zod_family(label: str) -> bool:
    return label.strip().upper() in {"F+","F-","V+","L+","V-","L-","SC","SD","SE"}

# ---------- structures ----------
@dataclass
class SourceRow:
    label_emit: str               # libellé à écrire (après normalisation éventuelle)
    data: Dict[str, str]          # toutes colonnes -> valeur brutes (on garde texte original)
    numeric_cols: List[str]       # pour mettre 0.0 si manquant

@dataclass
class SourceData:
    lang: LangSpec
    headers: List[str]
    label_col: str
    rows: Dict[str, SourceRow]    # clé normalisée -> row
    key_to_emit: Dict[str, str]   # pour récupérer un libellé quand l'autre côté n'a pas la ligne
    numeric_cols: List[str]

# ---------- lecture ----------
def read_source_csv(path: str) -> SourceData:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    with open(path, "rb") as fh:
        raw = fh.read()
    delim = sniff_delimiter(raw)
    text = raw.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    rows_list = [dict(r) for r in reader]
    headers = [h or "" for h in (reader.fieldnames or [])]
    if not rows_list:
        raise ValueError(f"CSV vide : {path}")

    lang = detect_lang(headers, rows_list)
    label_col = pick_label_column(headers)
    if not label_col:
        raise ValueError("Impossible d'identifier la colonne libellé (Élément/Element/Catégorie…).")

    num_cols = numeric_columns(headers, rows_list)

    def normalize_key(label: str) -> Tuple[str, str]:
        code = angular_to_internal(label, lang)
        if code: return ("ANGULAR", code)
        q = quadrant_internal(label, lang)
        if q is not None: return ("QUADRANT", f"Q{q}")
        if is_house(label, lang): return ("HOUSE", label)
        if is_hemisphere_like(label, lang): return ("HEMISPHERE", label)
        if is_aspect(label, lang): return ("ASPECT", label)
        if is_zod_family(label): return ("ZODFAM", label.strip().upper())
        if is_planet(label, lang): return ("PLANET", label)
        if is_sign(label, lang): return ("SIGN", label)
        return ("OTHER", label)

    rows: Dict[str, SourceRow] = {}
    key_to_emit: Dict[str, str] = {}

    for r in rows_list:
        raw_label = (r.get(label_col) or "").strip()
        if not raw_label:
            continue
        cat, key = normalize_key(raw_label)
        # filtrage aspects non canons
        if cat == "ASPECT":
            if lang is FR and raw_label not in FR_ASPECTS: 
                continue
            if lang is EN and raw_label not in EN_ASPECTS:
                continue

        # libellé à émettre
        if cat == "ANGULAR":
            emit = angular_emit(key, lang)
        elif cat == "QUADRANT":
            emit = quadrant_emit(int(key[1:]), lang)
        elif cat == "ZODFAM":
            emit = key
        else:
            emit = raw_label

        rows[key] = SourceRow(
            label_emit=emit,
            data=r,
            numeric_cols=num_cols
        )
        key_to_emit[key] = emit

    return SourceData(lang=lang, headers=headers, label_col=label_col,
                      rows=rows, key_to_emit=key_to_emit, numeric_cols=num_cols)

def input_order_keys(srcH: SourceData, srcF: SourceData) -> list[str]:
    """
    Ordre = ordre d'apparition dans H, puis complété par les clés propres à F
    dans l'ordre d'apparition de F.
    """
    order = []
    seen = set()
    # ordre H
    for k in srcH.rows.keys():
        order.append(k); seen.add(k)
    # compléter avec F
    for k in srcF.rows.keys():
        if k not in seen:
            order.append(k); seen.add(k)
    return order

# ---------- tri ----------
def sort_keys_for_output(keys: List[str], lang: LangSpec, category_hint: Optional[str]) -> List[str]:
    if category_hint == "HOUSE":
        # les clés HOUSE sont en fait les libellés ; on trie via house_index
        return sorted(keys, key=lambda k: house_index(k, lang))
    if category_hint == "QUADRANT":
        return sorted(keys, key=lambda k: int(k[1:]))  # Q0..Q3
    if category_hint == "HEMISPHERE":
        return keys
    if category_hint == "ANGULAR":
        order = {"AS":0,"MC":1,"DS":2,"FC":3}
        return sorted(keys, key=lambda k: order.get(k, 99))
    if category_hint == "ASPECT":
        frmap = {"Conjonction":0,"Opposition":1,"Carré":2,"Trigone":3,"Sextile":4}
        enmap = {"Conjunction":0,"Opposition":1,"Square":2,"Trine":3,"Sextile":4}
        # les clés sont des libellés; choisir la map selon langue
        return sorted(keys, key=lambda k: (frmap if lang is FR else enmap).get(k, 99))
    if category_hint == "ZODFAM":
        flat = [x for b in ZOD_FAMILIES_BLOCKS for x in b]
        return sorted(keys, key=lambda k: flat.index(k) if k in flat else 99)
    if category_hint == "PLANET":
        m = {n:i for i,n in enumerate(PLANETS_ORDER_FR if lang is FR else PLANETS_ORDER_EN)}
        return sorted(keys, key=lambda k: m.get(k, 999))
    if category_hint == "SIGN":
        m = {n:i for i,n in enumerate(SIGNS_ORDER_FR if lang is FR else SIGNS_ORDER_EN)}
        return sorted(keys, key=lambda k: m.get(k, 999))
    return keys  # ordre d'entrée sinon

def guess_category(keys: List[str], src: SourceData) -> Optional[str]:
    if all(k in {"AS","MC","DS","FC"} for k in keys): return "ANGULAR"
    if all(k.startswith("Q") for k in keys if k): return "QUADRANT"
    # pour HOUSE, on ne peut pas s'appuyer sur la clé brute : utiliser étiquette à émettre
    emit_labels = [src.key_to_emit.get(k, k) for k in keys]
    if all(is_house(lbl, src.lang) for lbl in emit_labels): return "HOUSE"
    if all(is_aspect(src.key_to_emit.get(k,k), src.lang) for k in keys): return "ASPECT"
    if all(is_zod_family(k) for k in keys): return "ZODFAM"
    if any(is_hemisphere_like(src.key_to_emit.get(k,k), src.lang) for k in keys): return "HEMISPHERE"
    if any(is_planet(src.key_to_emit.get(k,k), src.lang) for k in keys): return "PLANET"
    if any(is_sign(src.key_to_emit.get(k,k), src.lang) for k in keys): return "SIGN"
    return None

# ---------- fusion/écriture ----------
def merge_hf(h_csv_path: str, f_csv_path: str, out_csv_path: str) -> None:
    """
    Lit H et F (sorties GéoAstro), fusionne, écrit un CSV long H/F
    dont les colonnes = colonnes d'origine + colonne Groupe/Group.
    """
    srcH = read_source_csv(h_csv_path)
    srcF = read_source_csv(f_csv_path)
    lang = srcH.lang

    # union des clés et tri
    all_keys_sorted = input_order_keys(srcH, srcF)    

    # construction de l'en-tête final :
    # on part des headers H, on insère Groupe juste après la colonne libellé,
    # puis on rajoute toute colonne F manquante à la fin.
    base_headers = [h for h in srcH.headers]  # copie
    if lang.group_col not in base_headers:
        # position = juste après label_col
        pos = base_headers.index(srcH.label_col) + 1
        base_headers = base_headers[:pos] + [lang.group_col] + base_headers[pos:]
    # union avec colonnes F (hors doublons)
    for h in srcF.headers:
        if h not in base_headers:
            base_headers.append(h)

    # écriture
    os.makedirs(os.path.dirname(out_csv_path) or ".", exist_ok=True)
    with open(out_csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(base_headers)

        def write_row(key: str, group_label: str, src: SourceData):
            r = src.rows.get(key)
            # libellé à émettre pour la colonne label
            emit_label = (r.label_emit if r else (srcH.key_to_emit.get(key) or srcF.key_to_emit.get(key) or key))
            for_group = group_label

            # fabriquer la ligne en respectant l'ordre des colonnes finales
            row: Dict[str, str] = {}
            # démarrer avec données source si présentes
            if r is not None:
                row.update(r.data)

            # injecter le libellé normalisé + la colonne groupe
            row[src.label_col] = emit_label
            row[lang.group_col] = for_group

            # compléter les colonnes manquantes
            for col in base_headers:
                if col not in row:
                    # si col numérique connue → 0.0, sinon vide
                    if r is not None and col in r.numeric_cols:
                        row[col] = str(0.0)
                    else:
                        # si on n'a pas r (ligne manquante côté H/F), on met 0.0 pour
                        # toutes colonnes numériques connues globalement
                        if col in srcH.numeric_cols or col in srcF.numeric_cols:
                            row[col] = str(0.0)
                        else:
                            row[col] = ""

            # émettre ligne dans l'ordre exact de base_headers
            w.writerow([row.get(h, "") for h in base_headers])

        for key in all_keys_sorted:
            write_row(key, lang.group_H, srcH)
            write_row(key, lang.group_F, srcF)

# ---------- CLI ----------
def _cli():
    ap = argparse.ArgumentParser(description="Fusion H/F (GéoAstro) — garde les mêmes colonnes que la sortie + colonne Groupe/Group")
    ap.add_argument("--h", required=True, help="CSV Hommes (sortie GéoAstro)")
    ap.add_argument("--f", required=True, help="CSV Femmes (sortie GéoAstro)")
    ap.add_argument("--out", required=True, help="CSV de sortie (merged_hf.csv)")
    args = ap.parse_args()
    merge_hf(args.h, args.f, args.out)
    print(f"OK : CSV H/F généré → {args.out}")

# ---------- Mini-UI ----------
try:
    from tkinter import (
        Tk,
        Label,
        Button,
        Entry,
        StringVar,
        filedialog,
        messagebox,
        Text,
        END,
        DISABLED,
        NORMAL,
    )
except Exception:
    Tk = Label = Button = Entry = StringVar = filedialog = messagebox = Text = None
    END = DISABLED = NORMAL = None

# ---------- Mini-UI ----------
class HFMergeUI:
    def __init__(self):
        self.root = Tk()
        self.root.title("GéoAstro — Générateur CSV H/F")
        self.h_path = StringVar(); self.f_path = StringVar()

        Label(self.root, text="Fichier Hommes :").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        Entry(self.root, textvariable=self.h_path, width=70).grid(row=0, column=1, padx=8, pady=6)
        Button(self.root, text="Parcourir…", command=self.browse_h).grid(row=0, column=2, padx=8)

        Label(self.root, text="Fichier Femmes :").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        Entry(self.root, textvariable=self.f_path, width=70).grid(row=1, column=1, padx=8, pady=6)
        Button(self.root, text="Parcourir…", command=self.browse_f).grid(row=1, column=2, padx=8)

        Button(self.root, text="Générer CSV H/F", command=self.generate).grid(row=2, column=0, columnspan=3, pady=8)

        Label(self.root, text="Résumé :").grid(row=3, column=0, sticky="nw", padx=8)
        self.info = Text(self.root, width=92, height=12)
        self.info.grid(row=3, column=1, columnspan=2, padx=8, pady=6)
        self.info.config(state=DISABLED)

    def browse_h(self):
        p = filedialog.askopenfilename(title="CSV Hommes (sortie GéoAstro)", filetypes=[("CSV","*.csv"),("Tous","*.*")])
        if p: 
            self.h_path.set(p)
            self.refresh_info()

    def browse_f(self):
        p = filedialog.askopenfilename(title="CSV Femmes (sortie GéoAstro)", filetypes=[("CSV","*.csv"),("Tous","*.*")])
        if p: 
            self.f_path.set(p)
            self.refresh_info()

    def _set_info(self, txt: str):
        self.info.config(state=NORMAL); self.info.delete("1.0", END); self.info.insert("1.0", txt); self.info.config(state=DISABLED)

    def refresh_info(self):
        hp, fp = self.h_path.get().strip(), self.f_path.get().strip()
        if not (hp and fp): return
        try:
            sh = read_source_csv(hp); sf = read_source_csv(fp)
        except Exception as e:
            self._set_info(f"Erreur: {e}"); return

        union = {*sh.rows.keys(), *sf.rows.keys()}
        # tenter de synthétiser une somme si une colonne 'Pourcentage/Percentage' existe
        pct_cols = [c for c in (sh.headers if sh else []) if c.lower().startswith("pourcentage")] \
                 or [c for c in (sh.headers if sh else []) if c.lower().startswith("percentage")]
        sumH = sum(normalize_number(r.data.get(pct_cols[0], "")) for r in sh.rows.values()) if pct_cols else 0.0
        sumF = sum(normalize_number(r.data.get(pct_cols[0], "")) for r in sf.rows.values()) if pct_cols else 0.0

        txt = []
        txt.append(f"Langue détectée : {sh.lang.lang}")
        txt.append(f"Colonne libellé : {sh.label_col}")
        txt.append(f"Colonnes numériques détectées : {', '.join(sorted(set(sh.numeric_cols) | set(sf.numeric_cols)))}")
        txt.append(f"Éléments H : {len(sh.rows)} — Somme % H ≈ {round(sumH,2)}" if pct_cols else f"Éléments H : {len(sh.rows)}")
        txt.append(f"Éléments F : {len(sf.rows)} — Somme % F ≈ {round(sumF,2)}" if pct_cols else f"Éléments F : {len(sf.rows)}")
        txt.append(f"Union H ∪ F : {len(union)}")
        self._set_info("\n".join(txt))

    def generate(self):
        hp, fp = self.h_path.get().strip(), self.f_path.get().strip()
        if not (hp and fp):
            messagebox.showerror("Erreur", "Sélectionne les deux fichiers (H & F)."); return
        outp = filedialog.asksaveasfilename(title="Exporter CSV H/F", defaultextension=".csv",
                                            filetypes=[("CSV","*.csv")], initialfile="merged_hf.csv")
        if not outp: return
        try:
            merge_hf(hp, fp, outp)
        except Exception as e:
            messagebox.showerror("Erreur", str(e)); return
        messagebox.showinfo("Terminé", f"CSV H/F généré :\n{outp}")

def ui():
    if Tk is None:
        raise RuntimeError("Interface Tkinter indisponible dans cet environnement.")
    HFMergeUI().root.mainloop()

# ---------- main ----------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        _cli()
    else:
        ui()
