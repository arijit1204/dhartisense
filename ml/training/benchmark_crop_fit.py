"""Benchmark the crop ranking against real Indian district crop statistics.

Question: for a district and season, do the model's top 5 crops match the crops farmers there actually grow most (by area, 2008-2015)?
Variants compared on the same districts:
  fit only      EcoCrop requirements vs the district's weather history (no regional data)
  fit + nearby  the same, weighted by what the 5 nearest OTHER districts grow (the district itself is left out)
  nearby only   just the 5 crops grown on most land in those neighbouring districts (no weather model)
  national      the 5 most common crops in India that season (no weather, no location): the bar to beat
  random        5 random crops
Districts are split into dev and test halves: the blend weight (FIT_FLOOR) is chosen on dev only; read the TEST rows.
Run:  venv/Scripts/python.exe ml/training/benchmark_crop_fit.py   (first run downloads weather history, about 4 s per district)
Needs ml/models/regional_crops.json (ml/build_regional_crops.py).
"""

import collections
import datetime as dt
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
from app import server  # noqa: E402
from ml import crop_fit  # noqa: E402

CACHE = ROOT / "data/raw/crop_fit_benchmark_weather.json"
SEASONS = {"Kharif": (6, 25, False), "Rabi": (11, 5, True)}  # sowing date; whether irrigation is assumed (rabi is almost all irrigated in India)
N_DISTRICTS = 120


def pick_districts():
    ok = [d for d in crop_fit.REGIONAL if all(s in d["seasons"] for s in SEASONS)]
    random.Random(7).shuffle(ok)
    return sorted(ok[:N_DISTRICTS], key=lambda d: (d["state"], d["district"]))


def load_weather(districts):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    for i, d in enumerate(districts):
        key = f"{d['state']}|{d['district']}"
        if key not in cache:
            try:
                days = server.weather_history(d["lat"], d["lon"])
            except OSError:
                continue
            cache[key] = {x.isoformat(): v for x, v in days.items()}
            if i % 10 == 0:
                CACHE.write_text(json.dumps(cache))
                print("weather", i, "of", len(districts), flush=True)
    CACHE.write_text(json.dumps(cache))
    return {k: {dt.date.fromisoformat(x): tuple(v) for x, v in days.items()} for k, days in cache.items()}


def evaluate(districts, weather, floor, label, objective="fit"):
    national = {s: collections.Counter() for s in SEASONS}
    for d in crop_fit.REGIONAL:
        for s in SEASONS:
            for c, (share, _) in d["seasons"].get(s, {}).items():
                national[s][c] += share
    names = [c["name"] for c in crop_fit.CROPS]
    rng = random.Random(1)
    keyed = [d for d in districts if f"{d['state']}|{d['district']}" in weather]
    halves = (("dev", keyed[::2]), ("TEST", keyed[1::2]))
    print(f"\n{label}")
    scores = {}
    for split, ds in halves:
        tot = collections.defaultdict(lambda: [0.0, 0.0, 0])
        for d in ds:
            days = weather[f"{d['state']}|{d['district']}"]
            for season, (month, day, irrigated) in SEASONS.items():
                truth = {c: v[0] for c, v in d["seasons"][season].items()}
                top3 = {c for c, _ in sorted(truth.items(), key=lambda x: -x[1])[:3]}
                planting = dt.date(2026, month, day)
                near = crop_fit.nearby(d["lat"], d["lon"], season, skip=(d["state"], d["district"]))
                picks = {
                    "fit only": [o["crop"] for o in crop_fit.rank(days, planting, objective, irrigated=irrigated)["options"]],
                    "fit + nearby": [o["crop"] for o in crop_fit.rank(days, planting, objective, irrigated=irrigated, regional=near, fit_floor=floor)["options"]],
                    "nearby only": [c for c, _ in sorted(near["crops"].items(), key=lambda x: -x[1]["share"])[:5]] if near else [],
                    "national": [c for c, _ in national[season].most_common(5)],
                    "random": rng.sample(names, 5),
                }
                for who, p in picks.items():
                    tot[who][0] += len(top3 & set(p)) / 3
                    tot[who][1] += sum(truth.get(c, 0) for c in p)
                    tot[who][2] += 1
        for who, (hit, cover, n) in tot.items():
            print(f"  {split:4} {who:13} real top-3 crops found in the 5 picks: {hit / n:5.1%}   share of the district's cropped area covered: {cover / n:5.1%}   (n={n})")
            scores[(split, who)] = hit / n
    return scores


if __name__ == "__main__":
    districts = pick_districts()
    print(len(crop_fit.REGIONAL), "districts with data;", len(districts), "used")
    weather = load_weather(districts)
    best = None
    for floor in (0.0, 0.3, 0.5, 0.7, 0.9):
        s = evaluate(districts, weather, floor, f"FIT_FLOOR = {floor}")
        if best is None or s[("dev", "fit + nearby")] > best[1]:
            best = (floor, s[("dev", "fit + nearby")])
    print(f"\nbest FIT_FLOOR on dev: {best[0]} (compare with crop_fit.FIT_FLOOR = {crop_fit.FIT_FLOOR})")
