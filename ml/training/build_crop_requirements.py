"""Build ml/models/crop_requirements.json: the field crops we rank, with their FAO EcoCrop requirement ranges.

Source: FAO EcoCrop database (EcoCrop_DB.csv, from github.com/openclim/ecocrop) in data/raw/ecocrop/.
Display names are ours; every number comes straight from the database.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CROPS = {  # display name -> EcoCrop ScientificName
    "Rice": "Oryza sativa", "Wheat": "Triticum aestivum", "Maize": "Zea mays", "Sorghum (jowar)": "Sorghum bicolor",
    "Pearl millet (bajra)": "Pennisetum glaucum", "Foxtail millet": "Setaria italica", "Chickpea": "Cicer arietinum",
    "Pigeon pea": "Cajanus cajan", "Lentil": "Lens culinaris", "Green gram (moong)": "Vigna radiata", "Black gram (urad)": "Vigna mungo",
    "Cowpea": "Vigna unguiculata", "Field pea": "Pisum sativum", "Soybean": "Glycine max", "Groundnut": "Arachis hypogaea",
    "Mustard": "Brassica juncea", "Sunflower": "Helianthus annuus", "Sesame": "Sesamum indicum", "Safflower": "Carthamus tinctorius",
    "Linseed": "Linum usitatissimum", "Castor": "Ricinus communis", "Cotton": "Gossypium hirsutum", "Sugarcane": "Saccharum officinarum",
    "Barley": "Hordeum vulgare", "Potato": "Solanum tuberosum", "Tomato": "Lycopersicon esculentum", "Onion": "Allium cepa",
    "Chilli": "Capsicum annuum", "Brinjal (eggplant)": "Solanum melongena", "Okra": "Abelmoschus esculentus", "Cucumber": "Cucumis sativus",
    "Carrot": "Daucus carota", "Spinach": "Spinacia oleracea", "Radish": "Raphanus sativus", "Coriander": "Coriandrum sativum",
    "Fenugreek": "Trigonella foenum-graecum", "Turmeric": "Curcuma longa", "Ginger": "Zingiber officinale",
}  # left out on purpose: crops whose EcoCrop row is clearly off for Indian farming (cumin) or has no growing-season length (watermelon)
FIELDS = ["TMIN", "TOPMN", "TOPMX", "TMAX", "RMIN", "ROPMN", "ROPMX", "RMAX", "PHMIN", "PHOPMN", "PHOPMX", "PHMAX", "GMIN", "GMAX"]


def num(value):
    try:
        return float(value)
    except ValueError:
        return None


rows = {r["ScientificName"]: r for r in csv.DictReader(open(ROOT / "data/raw/ecocrop/EcoCrop_DB.csv", encoding="latin-1"))}
out = []
for name, sci in CROPS.items():
    r = rows[sci]  # KeyError here means a name is not in the database: fix the list, do not guess values
    entry = {"name": name, "scientific": sci, **{f: num(r[f]) for f in FIELDS}}
    entry["texture"] = [t.strip() for t in r["TEXT"].split(",") if t.strip() in ("light", "medium", "heavy", "wide")]
    entry["texture_ok"] = [t.strip() for t in r["TEXTR"].split(",") if t.strip() in ("light", "medium", "heavy", "wide")]
    assert all(entry[f] is not None for f in FIELDS), name
    out.append(entry)
(ROOT / "ml/models/crop_requirements.json").write_text(json.dumps({"source": "FAO EcoCrop (github.com/openclim/ecocrop EcoCrop_DB.csv)", "crops": out}, indent=1), encoding="utf-8")
print(len(out), "crops written")
