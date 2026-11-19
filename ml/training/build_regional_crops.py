"""Build ml/models/regional_crops.json from Indian government district crop statistics (Kaggle abhinand05/crop-production-in-india).

Per district: coordinates plus, for each season, every ranked crop's share of cropped area and its typical yield (tonnes per hectare), 2008-2015.
Coordinates come from Open-Meteo geocoding; districts that cannot be placed are left out. Resumable: coordinates are cached.
"""

import collections
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
from app import server  # noqa: E402

DATA = Path.home() / ".cache/kagglehub/datasets/abhinand05/crop-production-in-india/versions/1/crop_production.csv"
OUT = ROOT / "ml/models/regional_crops.json"
COORDS = ROOT / "data/raw/district_coords.json"
CROP_MAP = {"Rice": "Rice", "Wheat": "Wheat", "Maize": "Maize", "Jowar": "Sorghum (jowar)", "Bajra": "Pearl millet (bajra)", "Gram": "Chickpea",
            "Arhar/Tur": "Pigeon pea", "Masoor": "Lentil", "Moong(Green Gram)": "Green gram (moong)", "Urad": "Black gram (urad)", "Cowpea(Lobia)": "Cowpea",
            "Soyabean": "Soybean", "Groundnut": "Groundnut", "Rapeseed &Mustard": "Mustard", "Sunflower": "Sunflower", "Sesamum": "Sesame", "Safflower": "Safflower",
            "Linseed": "Linseed", "Castor seed": "Castor", "Cotton(lint)": "Cotton", "Barley": "Barley", "Potato": "Potato", "Onion": "Onion", "Dry chillies": "Chilli",
            "Coriander": "Coriander", "Brinjal": "Brinjal (eggplant)", "Sugarcane": "Sugarcane", "Turmeric": "Turmeric", "Dry ginger": "Ginger"}
SEASONS = ("Kharif", "Rabi", "Summer")
YEARS = range(2008, 2016)
SEASON_ALIAS = {"Autumn": "Kharif", "Winter": "Kharif"}  # the monsoon-sown rice seasons (aus, aman) of eastern India
YEAR_ROUND = {"Sugarcane", "Turmeric", "Ginger"}  # genuinely year-round crops; other "Whole Year" rows have no usable season and are skipped
# Cotton is reported in bales and sugarcane in tonnes of cane; yields stay per crop, never compared across crops.
# shortcut: Cotton(lint) production is in bales of 170 kg; converted to tonnes below.
BALE_T = 0.17


def geocode(state, district):
    name = district.title()
    for query in (name, f"{name} district"):
        for attempt in range(2):
            try:
                hits = server.geocode(query).get("results", [])
                break
            except OSError:
                time.sleep(1)
                hits = []
        for h in hits:
            if h.get("country_code") == "IN" and state.lower()[:5] in (h.get("admin1") or "").lower():
                return [round(h["latitude"], 3), round(h["longitude"], 3)]
    return None


area = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))  # (state, district, season) -> crop -> [ha, tonnes]
for r in csv.DictReader(open(DATA, encoding="utf-8")):
    crop = CROP_MAP.get(r["Crop"].strip())
    season = SEASON_ALIAS.get(r["Season"].strip(), r["Season"].strip())
    if not crop or not r["Area"] or not r["Production"] or int(r["Crop_Year"]) not in YEARS or season not in SEASONS + ("Whole Year",):
        continue
    if season == "Whole Year" and crop not in YEAR_ROUND:
        continue
    production = float(r["Production"]) * (BALE_T if crop == "Cotton" else 1)
    for s in SEASONS if season == "Whole Year" else (season,):  # year-round crops count in every season
        cell = area[(r["State_Name"].strip(), r["District_Name"].strip(), s)][crop]
        cell[0] += float(r["Area"])
        cell[1] += production

districts = sorted({(st, d) for st, d, _ in area})
coords = json.loads(COORDS.read_text()) if COORDS.exists() else {}
print(len(districts), "districts;", len(coords), "already placed", flush=True)
for i, (st, d) in enumerate(districts):
    key = f"{st}|{d}"
    if key not in coords:
        coords[key] = geocode(st, d)
        if i % 25 == 0:
            COORDS.write_text(json.dumps(coords))
            print(i, "of", len(districts), flush=True)
COORDS.write_text(json.dumps(coords))

out = []
for st, d in districts:
    if not coords.get(f"{st}|{d}"):
        continue
    seasons = {}
    for s in SEASONS:
        crops = area.get((st, d, s))
        if not crops:
            continue
        total = sum(a for a, _ in crops.values())
        if total < 1000:
            continue
        seasons[s] = {c: [round(a / total, 4), round(t / a, 3) if a else None] for c, (a, t) in crops.items() if a > 0}
    if seasons:
        out.append({"state": st, "district": d.title(), "lat": coords[f"{st}|{d}"][0], "lon": coords[f"{st}|{d}"][1], "seasons": seasons})
OUT.write_text(json.dumps({"source": "Indian government district crop statistics 2008-2015 (Kaggle abhinand05/crop-production-in-india)", "districts": out}, separators=(",", ":")), encoding="utf-8")
print(len(out), "districts placed and written")
