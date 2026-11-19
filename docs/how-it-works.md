# How it works

## Plant health model

Photo check is a cascade: the local classifier runs first (free, fast). When it is unsure, or the crop has only a healthy class, a Groq vision model (`GROQ_VISION_MODEL`, default `qwen/qwen3.8-27b`) adds a second opinion. Without a trained checkpoint the app uses the vision model alone.

Train the classifier in Colab with `ml/training/train_plant_disease_v3_colab.ipynb`, then copy `plant_disease_v3.pth` and `plant_disease_v3.metrics.json` into `ml/models/` and restart the server. The checkpoint carries its own labels, calibrated temperature and "unsure" threshold.

The free Groq tier limits the vision model to about 8,000 tokens a minute (roughly 3 photos a minute); the app reports this instead of failing silently.

## Crop ranking and field plan

The Crop plan page ranks crops for a saved field and planting date (`POST /api/crop-rank`, `ml/crop_fit.py`):

- what farmers in the 5 nearest districts grow in that season, with typical yields (Indian government district statistics 2008-2015; `ml/training/build_regional_crops.py`)
- adjusted by how well each crop's needs (FAO EcoCrop ranges; `ml/training/build_crop_requirements.py`) match five years of weather at the field (Open-Meteo archive), the field's pH and soil texture, and whether it is irrigated

Outside India there is no district data, so only the weather and soil fit is used. "Plan this field" (`static/fieldplan.js`) lays out rows, working paths and sprinkler or drip lines on the saved boundary.

## Field map

Layers (all free, no key): Esri "Clarity" satellite (default), classic Esri satellite, and an Esri place-name overlay (no street map). Place search uses OpenStreetMap's Nominatim and Photon (both open source) limited to India first, then worldwide; coordinates such as `18.52, 73.85` also work. Boundaries can be traced by tapping corners or drawn freehand for curved edges (simplified to at most about 120 corners). Esri imagery is free to use with attribution but is not open source, and its detail in rural India varies.

Interface language (Hindi, Marathi, Bengali, Tamil) covers the main menus, page titles and key buttons plus assistant answers; the wording has not been checked by native speakers (`static/ui.js`). Units (hectares/acres, °C/°F) are kept on the device.

## Crop health (satellite NDVI)

`app/ndvi.py` + `static/ndvi.js`: for the selected field's boundary, finds Sentinel-2 L2A scenes from the last five months (free, no key, via Microsoft's Planetary Computer STAC and data APIs), reads the average NDVI inside the boundary and its spread, and checks the scene classification layer so scenes with cloud or cloud shadow over THE FIELD are not used. The page shows a colour map for any chosen date, the share of the field that is weak / moderate / strong, a trend chart and plain-language notes. The latest reading is saved on the field and appears on the field card and in the report. Limits: 10 m pixels (fields under about 0.1 ha are refused), a clear image every few days at best, and NDVI depends on crop and growth stage, so the change over time matters more than any single value. It never diagnoses a cause. The Planetary Computer service is free for light use; for heavy public use, check its terms or move to your own tile service.

## Water and nutrients

Pick one or more suggested crops on the Water & nutrients page (`POST /api/water-plan`, `ml/water_plan.py`): FAO-56 daily soil-water balance using crop coefficients, stage lengths, root depth and depletion fraction from FAO-56 tables, with ET0 and rain from Open-Meteo (past and 16-day forecast). Crops FAO-56 does not list are marked "approximate". The farmer's soil observation and last irrigation date override the model. Fertiliser plan (`POST /api/nutrient-plan`, `ml/nutrient_plan.py`) works only from soil-test numbers the farmer types in (Soil Health Card ratings, ICAR 25% adjustment), so it needs no hardware. General doses are indicative; see the header of that file.

`ml/training/benchmark_crop_fit.py` scores the ranking against held-out districts' real crop areas. It measures agreement with local practice, not yield or profit.
