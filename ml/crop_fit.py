"""Rank crops for one field: FAO EcoCrop requirement ranges against the field's own weather history, pH and soil texture.

No training, no synthetic data. A crop's score says how well the place and season fit its published needs. It is not a yield forecast.
"""

import datetime as dt
import json
import math
from pathlib import Path

REQUIREMENTS = json.loads((Path(__file__).parent / "models" / "crop_requirements.json").read_text(encoding="utf-8"))
CROPS = REQUIREMENTS["crops"]
TEXTURE_CLASS = {"sand": "light", "loam": "medium", "silt loam": "medium", "clay loam": "medium", "clay": "heavy"}
MIN_YEARS = 3
REGIONAL_FILE = Path(__file__).parent / "models" / "regional_crops.json"
REGIONAL = json.loads(REGIONAL_FILE.read_text(encoding="utf-8"))["districts"] if REGIONAL_FILE.exists() else []
FIT_FLOOR = 0.5  # how much of a crop's regional score survives a zero fit (0 = fit decides everything, 1 = fit ignored); see ml/benchmark_crop_fit.py
MIN_SHOWN = 10  # below this score a crop is not offered as a pick
RULED_OUT = 0.1  # a temperature factor below this means the crop cannot grow here
DRY_SHARE = 0.3  # rain-fed with under 30% of the crop's minimum rain: nothing will grow without irrigation
MAX_KM = 400  # beyond this the nearest district data says nothing about the field


def season_of(planting):
    """India's cropping seasons: Kharif (monsoon) Jun-Sep, Rabi (winter) Oct-Jan, Summer Feb-May."""
    return "Kharif" if 6 <= planting.month <= 9 else "Rabi" if planting.month >= 10 or planting.month <= 1 else "Summer"


def nearby(lat, lon, season, k=5, skip=None):
    """What farmers in the k nearest districts grow in this season: {crop: {share, yield}}, plus the district names. None if the field is outside coverage."""
    rows = []
    for d in REGIONAL:
        if season not in d["seasons"] or (skip and (d["state"], d["district"]) == skip):
            continue
        a, b = math.radians(lat), math.radians(d["lat"])
        h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(d["lon"] - lon) / 2) ** 2
        rows.append((12742 * math.asin(math.sqrt(h)), d))
    rows.sort(key=lambda r: r[0])
    rows = rows[:k]
    if not rows or rows[0][0] > MAX_KM:
        return None
    total_w = shares = 0
    crops = {}
    for km, d in rows:
        w = 1 / (km + 30)
        total_w += w
        for crop, (share, yld) in d["seasons"][season].items():
            c = crops.setdefault(crop, {"share": 0.0, "yw": 0.0, "y": 0.0})
            c["share"] += w * share
            if yld:
                c["yw"] += w * share
                c["y"] += w * share * yld
    return {"crops": {n: {"share": c["share"] / total_w, "yield": round(c["y"] / c["yw"], 2) if c["yw"] else None} for n, c in crops.items()}, "districts": [f"{d['district']}, {d['state']}" for _, d in rows]}


def trapezoid(x, lo, opt_lo, opt_hi, hi):
    """1 inside the optimal range, falling linearly to 0 at the absolute limits."""
    if x <= lo or x >= hi:
        return 0.0
    if x < opt_lo:
        return (x - lo) / (opt_lo - lo)
    if x > opt_hi:
        return (hi - x) / (hi - opt_hi)
    return 1.0


def centred(x, lo, opt_lo, opt_hi, hi):
    """Trapezoid fit, nudged by how close x is to the middle of the optimal range, so crops that all fit still separate."""
    base = trapezoid(x, lo, opt_lo, opt_hi, hi)
    return base * (0.8 + 0.2 * max(0.0, 1 - abs(x - (opt_lo + opt_hi) / 2) / ((hi - lo) / 2)))


def cycle_days(crop):
    """Season length: the FAO-56 stage lengths when the crop has them (ml/water_plan.py), else a quarter of the way up EcoCrop's very wide range."""
    from ml import water_plan

    known = water_plan.CROP_WATER.get(crop["name"])
    if known:
        return sum(known[3])
    return max(30, round(crop["GMIN"] + 0.25 * (crop["GMAX"] - crop["GMIN"])))


def season_window(days, planting, length):
    """Per past year: (mean-temperature fit inputs, rainfall total) for the window starting on the planting date."""
    seasons = []
    for year in sorted({d.year for d in days}):
        try:
            start = dt.date(year, planting.month, planting.day)
        except ValueError:  # 29 Feb
            start = dt.date(year, 2, 28)
        window = [days.get(start + dt.timedelta(n)) for n in range(length)]
        if all(w is not None for w in window):
            seasons.append(window)
    return seasons


def texture_fit(crop, texture):
    wanted = TEXTURE_CLASS.get((texture or "").strip().lower())
    best, ok = crop["texture"], crop["texture_ok"]
    if not wanted or not (best or ok) or "wide" in best + ok:
        return None
    if wanted in best:
        return 1.0
    return 0.75 if wanted in ok else 0.3


def fit_crop(crop, days, planting, ph, texture, irrigated):
    length = cycle_days(crop)
    seasons = season_window(days, planting, length)
    if len(seasons) < MIN_YEARS:
        return None
    temp_fit = sum(sum(centred(t, crop["TMIN"], crop["TOPMN"], crop["TOPMX"], crop["TMAX"]) for t, _ in s) / length for s in seasons) / len(seasons)
    mean_temp = sum(sum(t for t, _ in s) / length for s in seasons) / len(seasons)
    rain = sum(sum(r for _, r in s) for s in seasons) / len(seasons)
    need = max(0.0, crop["ROPMN"] - rain) if irrigated else 0.0  # irrigation is assumed to make up a shortage, never an excess
    rain_fit = centred(max(rain, crop["ROPMN"]) if irrigated else rain, crop["RMIN"], crop["ROPMN"], crop["ROPMX"], crop["RMAX"])
    ph_fit = centred(ph, crop["PHMIN"], crop["PHOPMN"], crop["PHOPMX"], crop["PHMAX"]) if ph else None
    soil_fit = texture_fit(crop, texture)
    parts = [(temp_fit, 2), (rain_fit, 2)] + [(f, 1) for f in (ph_fit, soil_fit) if f is not None]
    score = 0.0 if any(f == 0 for f, _ in parts) else math.exp(sum(w * math.log(f) for f, w in parts) / sum(w for _, w in parts))
    reasons = [f"Season temperature averages {mean_temp:.0f} °C; this crop likes {crop['TOPMN']:.0f}–{crop['TOPMX']:.0f} °C."]
    reasons.append(f"Rain over the {length}-day season is about {rain:.0f} mm; irrigation makes up the rest." if irrigated else f"Rain over the {length}-day season is about {rain:.0f} mm; it likes {crop['ROPMN']:.0f}–{crop['ROPMX']:.0f} mm.")
    if ph_fit is not None:
        reasons.append(f"Your soil pH {ph:g}; it likes {crop['PHOPMN']:g}–{crop['PHOPMX']:g}.")
    return {
        "crop": crop["name"], "score": round(score * 100), "cycle_days": length, "reasons": reasons, "irrigation_mm": 0,
        "factors": {"temperature": round(temp_fit, 2), "rainfall": round(rain_fit, 2), "ph": None if ph_fit is None else round(ph_fit, 2), "soil": None if soil_fit is None else round(soil_fit, 2)},
        "season_temp": round(mean_temp, 1), "season_rain": round(rain), "water_need": crop["ROPMN"],
    }


def rank(days, planting, objective="fit", ph=None, texture=None, irrigated=False, picks=(), week=None, regional=None, fit_floor=FIT_FLOOR):
    """days: {date: (mean_temp, rain_mm)} history. week: {'temp': mean forecast temp, 'rain': mm} for a sowing-now check."""
    results = [r for r in (fit_crop(c, days, planting, ph, texture, irrigated) for c in CROPS) if r]
    by_name = {c["name"]: c for c in CROPS}
    top_share = max((c["share"] for c in regional["crops"].values()), default=0) if regional else 0
    for r in results:
        if regional:  # what farmers nearby actually grow leads; the crop's fit to this field's weather, pH and soil adjusts it
            local = regional["crops"].get(r["crop"])
            r["fit"] = r["score"]
            nearby_rel = local["share"] / top_share if local and top_share else 0
            r["score"] = round((0.05 + 0.95 * nearby_rel) * (fit_floor + (1 - fit_floor) * r["score"] / 100) * 100)
            dry = not irrigated and r["season_rain"] < DRY_SHARE * by_name[r["crop"]]["RMIN"]
            if r["factors"]["temperature"] < RULED_OUT or dry:  # weather rules the crop out: being common nearby does not rescue it
                r["score"] = min(r["score"], r["fit"])
            if local:
                r["regional"] = {"share": round(local["share"], 3), "yield": local["yield"]}
        r["label"] = "Good match" if r["score"] >= 75 else "Fair match" if r["score"] >= 55 else "Weak match"
        crop = by_name[r["crop"]]
        if week and 0 <= (planting - dt.date.today()).days <= 7 and not crop["TMIN"] <= week["temp"] <= crop["TMAX"]:
            r["sowing_note"] = f"This week's forecast ({week['temp']:.0f} °C) is outside what this crop tolerates, so wait to sow."
    keys = {
        "fit": lambda r: (-r["score"],),
        "risk": lambda r: (-min(f for f in r["factors"].values() if f is not None), -r["score"]),
        "water": lambda r: (r["score"] < 50, r["water_need"], -r["score"]),
    }
    key = keys.get(objective, keys["fit"])
    results.sort(key=lambda r: (r["score"] < MIN_SHOWN,) + key(r))  # crops below the cut-off always come last
    for i, r in enumerate(results, 1):
        r["rank"] = i
    shown = [r for r in results if r["score"] >= MIN_SHOWN][:5]
    wanted = {p.lower() for p in picks}
    return {"options": shown, "picks": [r for r in results if r not in shown and r["crop"].lower() in wanted], "ranked": len(results), "regional_districts": regional["districts"] if regional else []}
