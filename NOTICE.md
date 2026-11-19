# Third-party notices

Dhartisense's own source code is released under the [MIT licence](LICENSE). It uses data, services and libraries owned by others. This file lists them, what is known about their terms, and what this project does to respect them. It was prepared by reading the providers' public terms in November 2026; it is **not legal advice**, and terms change, so re-check anything you rely on, especially before commercial use.

## What is and is not in this repository

- **Included:** original source code, documentation, the product spec, and screenshots made with a demo account.
- **Not included (and git-ignored):** third-party datasets (`data/raw/`), derived data files (`ml/models/*.json`), and model weights (`*.pth`). Nothing is redistributed without a clear right to do so. Instructions to recreate them are in [docs/data-setup.md](docs/data-setup.md).
- **Not vendored:** no third-party library code is copied into the repository. Leaflet, Lucide and fonts are loaded from public CDNs at run time; Python packages are installed from PyPI.

## Data and reference tables

| Item | Where it is used | Source and terms | Status |
|---|---|---|---|
| FAO EcoCrop crop requirement ranges | built into `ml/models/crop_requirements.json` (not committed) | FAO EcoCrop database; the copy used is github.com/openclim/ecocrop, which has no licence file. FAO's EcoCrop page says the database was discontinued, so FAO's statistical-data terms (CC BY 4.0 with conditions) may not cover it. | **Unresolved.** Kept out of the repo. Credit FAO. Confirm terms with FAO or replace the source before commercial use |
| Indian district crop area and production, 2008-2015 | built into `ml/models/regional_crops.json` (not committed) | Government of India statistics (Directorate of Economics and Statistics), re-uploaded on Kaggle (`abhinand05/crop-production-in-india`). The Kaggle page's licence was not retrievable; related government portals publish similar data under open government licences. | **Unresolved for the Kaggle copy.** Kept out of the repo. Prefer the original government source for a public release |
| FAO-56 crop coefficients, stage lengths, rooting depths and depletion fractions | tables in `ml/water_plan.py` | Allen et al. (1998), FAO Irrigation and Drainage Paper 56. Numeric agronomic values; FAO is credited in the code and docs. Some crops use a related crop's values and are labelled "approximate". | Factual values with attribution. Do not copy FAO's text or tables wholesale |
| Fertiliser doses | table in `ml/nutrient_plan.py` | Tamil Nadu Agricultural University crop production guide, an FAI horticulture analysis, and typical national figures (each flagged in the code). | Indicative facts, attributed. Follow your state's recommendation |
| Soil-test rating limits (low/medium/high) | `ml/nutrient_plan.py` | Indian Soil Health Card ratings; ICAR 25% soil-test adjustment rule. | Published agronomic conventions |
| PlantVillage leaf images | trained the plant-photo model (weights not committed) | Hughes and Salathé (2015). The original paper and some mirrors state **CC BY-SA 3.0** (share-alike); other re-hosted copies say CC0. | **Share-alike may apply to models trained on it.** If you publish the weights, credit the dataset and consider releasing them under the same CC BY-SA terms, or leave them out (the deployment bundle leaves it out by default, see `deploy/build_bundle.py`) |
| PlantDoc leaf images | trained the plant-photo model | Public research dataset; its licence was not verified here. | **Verify** before publishing the weights |
| Crop Recommendation dataset (Hugging Face copy) | legacy baseline only, no longer used | See `data/manifest.yml`. | Not used by the app |

## Services called at run time

| Service | Used for | Terms to respect |
|---|---|---|
| Firebase Authentication and Firestore (Google) | accounts and field storage | Firebase / Google Cloud terms; free-plan quotas |
| Groq API | assistant and photo second opinion | Groq terms and rate limits; keys stay in your environment |
| Open-Meteo | weather, evapotranspiration, history | The free API is for **non-commercial** use, with fair-use limits (about 10,000 calls a day); data is CC BY 4.0, so keep the credit "Weather data by Open-Meteo.com" (shown in the footer). Commercial use needs a paid plan |
| Microsoft Planetary Computer and Copernicus Sentinel-2 | crop health | Sentinel-2 data is free and open; keep the credit "Contains modified Copernicus Sentinel data" (shown on the Crop health page). Check Planetary Computer's terms for heavy public use |
| Esri World Imagery, Clarity imagery and place names | satellite map layers | Esri's terms require visible attribution ("Esri, Maxar, Earthstar Geographics, and the GIS User Community", shown on the maps) and limit use beyond what Esri's licence allows. **Verify** Esri's current terms for a public site before launch; if in doubt, switch layers |
| OpenStreetMap Nominatim | place search | Public server for light use: at most about 1 request per second for the whole application; keep "© OpenStreetMap contributors". A busy site needs its own geocoder |
| Photon (komoot) | place search | Public demo server, fair-use and throttled with no guarantee; keep the OpenStreetMap credit |

## Software dependencies

| Package | Licence |
|---|---|
| firebase-admin (Python) | Apache-2.0 |
| Pillow | HPND (MIT-CMU style) |
| PyTorch and torchvision (optional, for the local plant model) | BSD-3-Clause |
| Leaflet (loaded from a CDN) | BSD-2-Clause |
| Lucide icons (loaded from a CDN) | ISC |
| DM Sans and Fraunces fonts (loaded from Google Fonts) | SIL Open Font License 1.1 |

All are compatible with the MIT licence of this project. Licences are as published by each project; re-check when you upgrade a package.

## Names, trademarks and disclaimer

"Dhartisense" is the name of this project. When it was chosen (November 2026), searches of the web, domain registries, GitHub and PyPI found no existing product or company with that exact name, but no trademark has been registered for it and the official trademark registers were not searched. Check IP India, WIPO and USPTO before relying on the name commercially.

Firebase, Google, Microsoft, Esri, Groq, Hugging Face, OpenStreetMap, Copernicus and other names belong to their owners and are used only to describe what the software works with; this project is not affiliated with or endorsed by them.

The software gives general guidance only. It is not agronomic, financial, legal or medical advice, and photo or satellite readings do not diagnose a cause. It is provided "as is" under the MIT licence, without warranty.
