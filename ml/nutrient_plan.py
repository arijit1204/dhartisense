"""Fertiliser plan from the farmer's own soil-test numbers (no sensor needed).

1. Rate each soil-test value low / medium / high with the Indian Soil Health Card limits (available N, Olsen P, ammonium-acetate K, kg/ha).
2. Start from the crop's general recommended dose (N : P2O5 : K2O kg/ha) and raise it 25% for a low rating or cut it 25% for a high one, the usual
   ICAR soil-test adjustment. No test value for a nutrient means the general dose is used and says so.
3. Turn nutrients into fertiliser (urea, DAP, MOP), split nitrogen over the crop's stages, and total it for the field.

The general doses are indicative national figures. Doses marked "checked" matched a published guide read for this project (TNAU Crop Production Guide 2020
or the FAI horticulture analysis); the rest are typical values, not looked up. State recommendations differ, so a Soil Health Card dose or the local
extension advice should override these.
"""

import datetime as dt

# crop: (N, P2O5, K2O kg/ha, checked)
DOSE = {
    "Rice": (120, 60, 40, False), "Wheat": (120, 60, 40, False), "Maize": (120, 60, 40, False), "Sorghum (jowar)": (90, 45, 45, True),
    "Pearl millet (bajra)": (70, 35, 35, True), "Foxtail millet": (40, 20, 20, False), "Chickpea": (20, 40, 20, False), "Pigeon pea": (25, 50, 25, False),
    "Lentil": (20, 40, 20, False), "Green gram (moong)": (20, 40, 20, False), "Black gram (urad)": (20, 40, 20, False), "Cowpea": (25, 50, 25, False),
    "Field pea": (20, 50, 40, False), "Soybean": (30, 60, 40, False), "Groundnut": (20, 40, 40, False), "Mustard": (80, 40, 40, False),
    "Sunflower": (60, 90, 60, False), "Sesame": (50, 25, 25, True), "Safflower": (60, 40, 20, False), "Linseed": (60, 30, 30, False),
    "Castor": (60, 30, 30, True), "Cotton": (100, 50, 50, False), "Sugarcane": (250, 85, 115, False), "Barley": (60, 30, 20, False),
    "Potato": (150, 80, 100, False), "Tomato": (120, 80, 60, False), "Onion": (120, 90, 90, True), "Chilli": (100, 50, 50, False),
    "Brinjal (eggplant)": (100, 50, 50, False), "Okra": (100, 50, 50, False), "Cucumber": (100, 50, 50, False), "Carrot": (60, 40, 50, False),
    "Spinach": (60, 40, 40, False), "Radish": (50, 50, 50, False), "Coriander": (60, 40, 30, True), "Fenugreek": (20, 40, 20, False),
    "Turmeric": (120, 60, 120, False), "Ginger": (75, 50, 50, False),
}
LEGUMES = {"Chickpea", "Pigeon pea", "Lentil", "Green gram (moong)", "Black gram (urad)", "Cowpea", "Field pea", "Soybean", "Groundnut", "Fenugreek"}
# Soil Health Card limits (kg/ha): below the first = low, above the second = high.
LIMITS = {"N": (280, 560), "P": (10, 25), "K": (110, 280)}
ADJUST = {"low": 1.25, "medium": 1.0, "high": 0.75, "unknown": 1.0}
NAMES = {"N": "Nitrogen", "P": "Phosphorus", "K": "Potassium"}


def rate(nutrient, value):
    if value is None:
        return "unknown"
    low, high = LIMITS[nutrient]
    return "low" if value < low else "high" if value > high else "medium"


def fertiliser(n, p2o5, k2o):
    """kg per hectare of DAP, urea and MOP that supply the nutrients (DAP is 18-46-0, urea 46% N, MOP 60% K2O)."""
    dap = p2o5 / 0.46
    urea = max(0.0, n - 0.18 * dap) / 0.46
    return {"DAP": dap, "Urea": urea, "MOP": k2o / 0.60}


def splits(crop, planting, season_days):
    """Nitrogen applications as (share, days after planting, label). Legumes fix their own nitrogen, so they get it all at sowing."""
    if crop in LEGUMES:
        return [(1.0, 0, "At sowing")]
    if season_days > 200:  # long crops such as sugarcane and turmeric
        return [(0.25, 0, "At planting"), (0.25, round(0.15 * season_days), "Early growth"), (0.25, round(0.3 * season_days), "Grand growth"), (0.25, round(0.5 * season_days), "Before peak growth")]
    return [(0.5, 0, "At sowing"), (0.25, round(0.3 * season_days), "Active growth"), (0.25, round(0.55 * season_days), "Flowering")]


def plan(crop, planting, area_ha, soil, season_days):
    """soil: {'N': kg/ha or None, 'P': ..., 'K': ...}. Returns the plan dict for one crop."""
    n, p, k, checked = DOSE[crop]
    general = {"N": n, "P": p, "K": k}
    ratings = {x: rate(x, soil.get(x)) for x in "NPK"}
    dose = {x: round(general[x] * ADJUST[ratings[x]]) for x in "NPK"}
    products = fertiliser(dose["N"], dose["P"], dose["K"])
    area = area_ha or 0
    rows = [{"share": s, "day": d, "label": lab, "date": (planting + dt.timedelta(d)).isoformat() if planting else None, "n_kg_ha": round(dose["N"] * s)} for s, d, lab in splits(crop, planting, season_days)]
    return {"crop": crop, "checked": checked, "general": general, "ratings": ratings, "dose": dose,
            "products_kg_ha": {k_: round(v) for k_, v in products.items()},
            "field_kg": {k_: round(v * area) for k_, v in products.items()} if area else None,
            "applications": rows, "legume": crop in LEGUMES}


if __name__ == "__main__":
    assert rate("N", 200) == "low" and rate("P", 15) == "medium" and rate("K", 400) == "high" and rate("K", None) == "unknown"
    r = plan("Wheat", dt.date(2026, 11, 1), 2.0, {"N": 200, "P": 30, "K": None}, 120)
    assert r["dose"] == {"N": 150, "P": 45, "K": 40}, r["dose"]  # low N +25%, high P -25%, K untested
    assert abs(sum(a["n_kg_ha"] for a in r["applications"]) - 150) <= 1
    f = r["products_kg_ha"]
    assert abs(0.46 * f["Urea"] + 0.18 * f["DAP"] - 150) <= 1 and r["field_kg"]["Urea"] == 2 * f["Urea"] or abs(r["field_kg"]["Urea"] - 2 * f["Urea"]) <= 1
    assert plan("Chickpea", dt.date(2026, 11, 1), 1, {}, 100)["applications"][0]["share"] == 1.0
    print("nutrient_plan self-check passed:", r["dose"], r["products_kg_ha"])
