"""Irrigation scheduling by the FAO-56 daily soil-water balance (Allen et al. 1998, FAO Irrigation and Drainage Paper 56).

Daily: depletion += crop water use (ETc = Kc x ET0) - effective rain. When depletion passes the readily available water (RAW = p x TAW)
the crop is stressed, so irrigate back to field capacity. ET0 and rain come from Open-Meteo (live, model-based, not a field sensor).
Crop numbers (Kc, stage lengths, rooting depth, p) are FAO-56 Tables 11, 12 and 22. Crops FAO-56 does not list borrow a close relative
(see `basis`) and their stage lengths are estimates, shown to the farmer as "approximate".
"""

import datetime as dt

# name: (Kc ini, Kc mid, Kc end, (initial, development, mid, late stage days), max root depth m, p, basis)
# "FAO-56" = every number from the tables; otherwise the text says what was borrowed or estimated.
CROP_WATER = {
    "Rice": (1.05, 1.20, 0.75, (30, 30, 60, 30), 0.75, 0.20, "FAO-56"),
    "Wheat": (0.30, 1.15, 0.30, (15, 25, 50, 30), 1.25, 0.55, "FAO-56 (central India row)"),
    "Maize": (0.30, 1.20, 0.48, (20, 35, 40, 30), 1.35, 0.55, "FAO-56 (India row)"),
    "Sorghum (jowar)": (0.30, 1.05, 0.55, (20, 35, 45, 30), 1.50, 0.55, "FAO-56"),
    "Pearl millet (bajra)": (0.30, 1.00, 0.30, (15, 25, 40, 25), 1.50, 0.55, "FAO-56 (millet)"),
    "Foxtail millet": (0.30, 1.00, 0.30, (15, 25, 40, 25), 1.50, 0.55, "approximate: FAO-56 millet"),
    "Chickpea": (0.40, 1.00, 0.35, (20, 30, 50, 30), 0.80, 0.50, "approximate: FAO-56 Kc, estimated stage lengths"),
    "Pigeon pea": (0.40, 1.15, 0.35, (25, 40, 70, 40), 0.80, 0.45, "approximate: FAO-56 pulses Kc, estimated stage lengths"),
    "Lentil": (0.40, 1.10, 0.30, (20, 30, 60, 40), 0.70, 0.50, "FAO-56"),
    "Green gram (moong)": (0.40, 1.05, 0.48, (20, 30, 30, 20), 0.80, 0.45, "FAO-56 (green gram and cowpea)"),
    "Black gram (urad)": (0.40, 1.05, 0.48, (20, 30, 30, 20), 0.80, 0.45, "approximate: FAO-56 green gram"),
    "Cowpea": (0.40, 1.05, 0.48, (20, 30, 30, 20), 0.80, 0.45, "FAO-56 (green gram and cowpea)"),
    "Field pea": (0.40, 1.15, 0.30, (20, 30, 35, 15), 0.80, 0.40, "FAO-56 (dry peas)"),
    "Soybean": (0.40, 1.15, 0.50, (15, 15, 40, 15), 0.95, 0.50, "FAO-56 (tropics row)"),
    "Groundnut": (0.40, 1.15, 0.60, (25, 35, 45, 25), 0.75, 0.50, "FAO-56"),
    "Mustard": (0.35, 1.08, 0.35, (20, 30, 40, 30), 1.25, 0.60, "approximate: FAO-56 rapeseed Kc, estimated stage lengths"),
    "Sunflower": (0.35, 1.08, 0.35, (25, 35, 45, 25), 1.15, 0.45, "FAO-56"),
    "Sesame": (0.35, 1.10, 0.25, (20, 30, 40, 20), 1.25, 0.60, "FAO-56"),
    "Safflower": (0.35, 1.08, 0.25, (20, 35, 45, 25), 1.50, 0.60, "FAO-56"),
    "Linseed": (0.35, 1.10, 0.25, (20, 30, 45, 25), 1.25, 0.50, "approximate: FAO-56 flax Kc, estimated stage lengths"),
    "Castor": (0.35, 1.15, 0.55, (20, 40, 50, 25), 1.50, 0.50, "FAO-56"),
    "Cotton": (0.35, 1.18, 0.60, (30, 50, 60, 55), 1.35, 0.65, "FAO-56"),
    "Sugarcane": (0.40, 1.25, 0.75, (35, 60, 190, 120), 1.60, 0.65, "FAO-56 (low latitudes)"),
    "Barley": (0.30, 1.15, 0.25, (15, 25, 50, 30), 1.25, 0.55, "FAO-56 (central India row)"),
    "Potato": (0.50, 1.15, 0.75, (25, 30, 45, 30), 0.50, 0.35, "FAO-56"),
    "Tomato": (0.60, 1.15, 0.80, (30, 40, 40, 25), 1.10, 0.40, "FAO-56"),
    "Onion": (0.70, 1.05, 0.75, (15, 25, 70, 40), 0.45, 0.30, "FAO-56"),
    "Chilli": (0.60, 1.05, 0.90, (25, 35, 40, 20), 0.75, 0.30, "approximate: FAO-56 sweet pepper"),
    "Brinjal (eggplant)": (0.60, 1.05, 0.90, (30, 40, 40, 20), 0.95, 0.45, "FAO-56"),
    "Okra": (0.60, 1.05, 0.90, (20, 30, 30, 20), 0.95, 0.45, "approximate: FAO-56 eggplant Kc, estimated stage lengths"),
    "Cucumber": (0.60, 1.00, 0.75, (20, 30, 40, 15), 0.95, 0.50, "FAO-56"),
    "Carrot": (0.70, 1.05, 0.95, (20, 30, 40, 20), 0.75, 0.35, "FAO-56"),
    "Spinach": (0.70, 1.00, 0.95, (20, 20, 20, 5), 0.40, 0.20, "FAO-56"),
    "Radish": (0.70, 0.90, 0.85, (5, 10, 15, 5), 0.40, 0.30, "FAO-56"),
    "Coriander": (0.70, 1.00, 0.95, (20, 25, 30, 15), 0.40, 0.30, "approximate: FAO-56 small vegetables"),
    "Fenugreek": (0.70, 1.00, 0.95, (20, 25, 30, 15), 0.40, 0.30, "approximate: FAO-56 small vegetables"),
    "Turmeric": (0.50, 1.10, 0.95, (30, 50, 110, 60), 0.50, 0.40, "approximate: FAO-56 roots and tubers group, estimated stage lengths"),
    "Ginger": (0.50, 1.10, 0.95, (30, 50, 100, 50), 0.40, 0.40, "approximate: FAO-56 roots and tubers group, estimated stage lengths"),
}
# shortcut: typical plant-available water (mm per metre of soil) by texture, from general soil-physics values rather than a per-field measurement. Replace with the farmer's soil test when available.
AWC = {"sand": 80, "loam": 140, "silt loam": 170, "clay loam": 160, "clay": 150}
DEFAULT_AWC = 140
# Share of applied water the crop actually gets, by method (typical field efficiencies, FAO Irrigation Manual).
EFFICIENCY = {"drip": 0.90, "sprinkler": 0.75, "furrow": 0.60, "flood": 0.55}
DEFAULT_EFFICIENCY = 0.65
OBSERVATION = {"Dry and dusty": 1.0, "Dry below the surface": 0.8, "Moist": 0.4, "Wet": 0.15, "Standing water": 0.0}  # share of RAW already used up, as seen in the field
# Largest net depth one irrigation can usefully apply (mm): lighter for drip and sprinklers, heavier for surface irrigation. Caps the allowed depletion,
# so a deep-rooted crop is irrigated more often with practical amounts instead of one huge refill.
MAX_NET = {"drip": 25, "sprinkler": 50, "furrow": 75, "flood": 75}
DEFAULT_MAX_NET = 60
HORIZON = 14


def eff_rain(mm):
    return 0.8 * mm if mm >= 3 else 0.0  # showers under 3 mm wet the surface and evaporate


def stage_info(crop, day):
    """(stage name, Kc, root depth m, season length) on `day` days after planting."""
    kc_ini, kc_mid, kc_end, (a, b, c, d), zr, _, _ = crop
    if day < a:
        name, kc = "Establishment", kc_ini
    elif day < a + b:
        name, kc = "Vegetative growth", kc_ini + (kc_mid - kc_ini) * (day - a) / b
    elif day < a + b + c:
        name, kc = "Flowering and yield formation", kc_mid
    else:
        name, kc = "Ripening", kc_mid + (kc_end - kc_mid) * min(1.0, (day - a - b - c) / d)
    root = min(zr, 0.25 + (zr - 0.25) * min(1.0, day / (a + b)))  # roots deepen until the end of the vegetative stage
    return name, kc, root, a + b + c + d


def simulate(crop, planting, weather, awc, efficiency, start, depletion, auto, end, cap=DEFAULT_MAX_NET):
    """Step the soil-water balance from `start` to `end` (inclusive).
    depletion: mm already missing from the root zone before `start`. auto: assume the farmer irrigates whenever the crop would be stressed.
    Returns daily rows [{date, stage, etc, rain, depletion, raw, irrigated_net}], ending depletion."""
    rows = []
    day = start
    while day <= end:
        if day not in weather or day < planting:
            day += dt.timedelta(1)
            continue
        et0, rain = weather[day]
        name, kc, root, length = stage_info(crop, (day - planting).days)
        if (day - planting).days >= length:
            break
        taw = awc * root
        raw = min(crop[5] * taw, cap)
        etc = kc * et0
        depletion = max(0.0, depletion + etc - eff_rain(rain))
        given = 0.0
        if auto and depletion >= raw:
            given, depletion = depletion, 0.0
        rows.append({"date": day, "stage": name, "etc": etc, "rain": rain, "depletion": depletion, "raw": raw, "irrigated_net": given, "kc": kc, "root": root})
        day += dt.timedelta(1)
    return rows, depletion


def schedule(name, planting, today, weather, texture=None, method=None, last_irrigation=None, observation=None):
    """Plan for one crop. weather: {date: (et0_mm, rain_mm)} covering the past and the forecast. Dates are datetime.date."""
    crop = CROP_WATER[name]
    awc = AWC.get((texture or "").strip().lower(), DEFAULT_AWC)
    eff = EFFICIENCY.get((method or "").strip().lower(), DEFAULT_EFFICIENCY)
    cap = MAX_NET.get((method or "").strip().lower(), DEFAULT_MAX_NET)
    stage, kc, root, length = stage_info(crop, max(0, (today - planting).days))
    out = {"crop": name, "basis": crop[6], "approximate": crop[6].startswith("approximate"), "season_days": length, "efficiency": eff, "awc_mm_per_m": awc}
    if today < planting:
        out.update(status="before_sowing", days_to_sowing=(planting - today).days)
        return out
    day_no = (today - planting).days
    if day_no >= length:
        out.update(status="season_over")
        return out
    # Past: from the last irrigation if the farmer gave one (nothing assumed after it), otherwise assume irrigation whenever the crop was stressed.
    known = last_irrigation is not None and planting <= last_irrigation <= today
    start = last_irrigation if known else planting
    past, depletion = simulate(crop, planting, weather, awc, eff, start, 0.0, not known, today, cap)
    basis = "your last irrigation date" if known else "an assumed schedule (no last irrigation date given)"
    stage, kc, root, _ = stage_info(crop, day_no)
    raw_now = min(crop[5] * awc * root, cap)
    seen = OBSERVATION.get(observation or "")
    if seen is not None:  # what the farmer sees today beats the model
        depletion = seen * raw_now
        basis = f"your observation: {observation.lower()}"
    if known and seen is not None and seen >= 0.8 and (today - last_irrigation).days <= 5:
        out["note"] = f"You irrigated {(today - last_irrigation).days} day(s) ago but the soil looks dry. Check that the water reached the whole field; very light soil or uneven application can cause this."
    out.update(stage=stage, day_of_season=day_no + 1, kc=round(kc, 2), root_m=round(root, 2), taw_mm=round(awc * root), raw_mm=round(raw_now), depletion_mm=round(depletion), basis_of_now=basis)
    # Future: the forecast days, with no irrigation, to find the first day the crop runs short.
    future, _ = simulate(crop, planting, weather, awc, eff, today + dt.timedelta(1), depletion, False, today + dt.timedelta(HORIZON), cap)
    week = future[:7]
    out["week"] = {"etc_mm": round(sum(r["etc"] for r in week), 1), "rain_mm": round(sum(r["rain"] for r in week), 1)}
    out["days"] = [{"date": r["date"].isoformat(), "etc": round(r["etc"], 1), "rain": round(r["rain"], 1), "depletion": round(r["depletion"]), "raw": round(r["raw"])} for r in future]
    if depletion >= raw_now:
        due, need = today, depletion
    else:
        due = need = None
        for r in future:
            if r["depletion"] >= r["raw"]:
                due, need = r["date"], r["depletion"]
                break
    coming = sum(eff_rain(r["rain"]) for r in future[:3])
    if due == today and coming >= 0.6 * need:  # rain in the next 3 days refills most of what is missing, so irrigating now would waste water
        out.update(status="wait_rain", rain_mm=round(sum(r["rain"] for r in future[:3]), 1), net_mm=round(need), gross_mm=round(need / eff))
    elif due is None:
        out.update(status="not_needed")
    else:
        out.update(status="now" if due == today else "soon", due=due.isoformat(), in_days=(due - today).days, net_mm=round(need), gross_mm=round(need / eff))
    return out


def outlook(name, planting, history, texture=None, method=None):
    """Planting is in the future: replay the same dates in past years and report the typical season (water use, rain, irrigation needed)."""
    crop = CROP_WATER[name]
    awc = AWC.get((texture or "").strip().lower(), DEFAULT_AWC)
    eff = EFFICIENCY.get((method or "").strip().lower(), DEFAULT_EFFICIENCY)
    cap = MAX_NET.get((method or "").strip().lower(), DEFAULT_MAX_NET)
    length = stage_info(crop, 0)[3]
    seasons = []
    for year in sorted({d.year for d in history}):
        try:
            start = dt.date(year, planting.month, planting.day)
        except ValueError:
            start = dt.date(year, 2, 28)
        if all(start + dt.timedelta(n) in history for n in range(length)):
            rows, _ = simulate(crop, start, history, awc, eff, start, 0.0, True, start + dt.timedelta(length), cap)
            given = [((r["date"] - start).days, r["irrigated_net"]) for r in rows if r["irrigated_net"]]
            seasons.append((sum(r["etc"] for r in rows), sum(r["rain"] for r in rows), sum(r["irrigated_net"] for r in rows), len(given), given))
    if len(seasons) < 3:
        return {"crop": name, "status": "no_history"}
    n = len(seasons)
    mean = lambda i: sum(s[i] for s in seasons) / n  # noqa: E731
    median = lambda v: sorted(v)[len(v) // 2]  # noqa: E731
    rounds = []
    for i in range(round(mean(3))):  # the i-th irrigation of the season, typically this many days after planting and this deep
        same = [s[4][i] for s in seasons if len(s[4]) > i]
        rounds.append({"day": median([d for d, _ in same]), "net_mm": round(median([m for _, m in same])), "gross_mm": round(median([m for _, m in same]) / eff)})
    return {"crop": name, "status": "outlook", "rounds": rounds, "basis": crop[6], "approximate": crop[6].startswith("approximate"), "season_days": length, "years": n, "efficiency": eff,
            "etc_mm": round(mean(0)), "rain_mm": round(mean(1)), "net_mm": round(mean(2)), "gross_mm": round(mean(2) / eff), "irrigations": round(mean(3))}


if __name__ == "__main__":  # self-check: constant 5 mm/day ET0, no rain, wheat on loam
    p = dt.date(2026, 11, 1)
    w = {p + dt.timedelta(n): (5.0, 0.0) for n in range(200)}
    today = p + dt.timedelta(60)  # mid-season, last irrigated 12 days ago
    plan = schedule("Wheat", p, today, w, "loam", "sprinkler", today - dt.timedelta(12))
    assert plan["status"] in ("now", "soon") and plan["gross_mm"] > plan["net_mm"] > 0, plan
    assert schedule("Wheat", p, p - dt.timedelta(3), w)["status"] == "before_sowing"
    assert schedule("Wheat", p, p + dt.timedelta(300), w)["status"] == "season_over"
    wet = {k: (5.0, 20.0) for k in w}  # daily heavy rain keeps the soil full
    assert schedule("Wheat", p, today, wet, "loam")["status"] == "not_needed"
    print("water_plan self-check passed:", plan["status"], plan.get("in_days"), plan["net_mm"], "mm net")
