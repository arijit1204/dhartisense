# Dhartisense — Product Requirements Document

**Document status:** Product and research specification  
**Version:** 1.0  
**Date:** 3 November 2026  
**Product type:** GenAI-enabled, completely free farmer-first web tool with a mobile-first progressive web application  
**Primary users:** Small and medium farmers

## 1. Executive summary

Dhartisense is a complete digital farm-advisory platform. A farmer creates a farm, marks one or more field boundaries on a free web map, enters available soil and management information, selects a crop and crop stage, and receives recommendations that are specific to that field and season.

The platform combines:

1. Field geometry and location context.
2. Farmer-entered soil, crop, irrigation and management observations.
3. Public weather and climate data.
4. Public soil-map context where available.
5. Trained machine-learning models for crop suitability, yield forecasting and disease image classification.
6. A retrieval-augmented agricultural assistant powered by the Groq API.
7. A deterministic rules and evidence layer that checks generated advice before it is shown.

The central research contribution is a **Context-Aware Agricultural Recommendation Engine (CARE)**. CARE does not treat an ML prediction or an LLM answer as a complete recommendation. It fuses the prediction with location, season, soil, crop stage, disease risk, historical observations, water availability and farmer priorities, then returns an explainable ranked action plan with confidence, evidence, assumptions and missing-data warnings.

The system is advisory software, not an autonomous control system. It is deliberately designed without hardware integration. It cannot measure live soil moisture, pump flow, nutrient concentration or field temperature. Irrigation and fertilizer advice must therefore be based on farmer-entered observations, public weather data, crop-stage requirements and optional map-derived context. Every report must label whether a value is **measured by the farmer**, **estimated**, **retrieved from a public data source**, or **predicted by a model**.

## 2. Problem statement

Farmers commonly receive generic crop and input advice. Generic recommendations fail to account for:

- Soil pH, texture, drainage and nutrient status in the specific field.
- The field's location, elevation, area and boundary.
- Current and forecast weather.
- Planting date and crop growth stage.
- Existing disease symptoms and recent disease history.
- Actual water source, irrigation method and water availability.
- Farmer risk tolerance, budget, labour and market priorities.
- Historical yield and management records.
- Local language and literacy needs.

Current digital tools are also fragmented. One tool may identify a leaf disease, another may show weather, and another may recommend a crop. The farmer or advisor must manually connect these outputs. A high-accuracy laboratory disease classifier can still fail on a field photograph, and a language model can produce confident but unsafe advice when it is not grounded in local evidence.

### 2.1 Consequences

- Wrong crop selection and avoidable crop failure.
- Over- or under-irrigation when no sensor data is available.
- Unnecessary fertilizer expense and nutrient runoff.
- Late disease recognition.
- Advice that is difficult to understand or not available in the farmer's language.
- No traceable record of why a recommendation was made.

### 2.2 Product opportunity

Farmers need a simple mobile-first platform rather than a collection of disconnected weather, disease and crop applications. Dhartisense brings field mapping, farmer-entered observations, public data, trained ML models and a local-language agricultural assistant into one personal farm workspace.

## 3. Product vision and goals

### Vision

Make evidence-based, localised and understandable agricultural advice available for every mapped field, even when the farmer has no IoT devices.

### Goals

1. Give every farm a map-based digital identity.
2. Convert farmer inputs and public data into a structured field context.
3. Recommend suitable crops and explain the main suitability factors.
4. Forecast yield with honest uncertainty and a data-quality score.
5. Provide stage-aware irrigation and fertilizer guidance without pretending to observe sensors.
6. Identify likely crop diseases from photographs and route uncertain cases for expert review.
7. Provide cited, local-language agricultural answers through RAG and Groq.
8. Keep recommendations auditable: inputs, model version, sources, timestamp and assumptions are stored.
9. Provide a publishable evaluation of whether context-aware recommendations outperform isolated models and generic LLM advice.

### Non-goals

- Automatic pump, valve, drone or farm-equipment control.
- Claiming real-time soil moisture or nutrient measurements without farmer data or a connected sensor.
- Replacing an agronomist, plant pathologist or legally required pesticide label.
- Universal accuracy for every crop, country, disease or language at initial launch.
- Generating or fabricating training data.

## 4. Target users and roles

### 4.1 Farmer

Creates farms and fields, marks boundaries, enters observations, uploads images, views recommendations, asks questions and downloads reports. The primary interface must work on a low-end Android phone and tolerate intermittent connectivity.

### 4.2 Platform administrator

Manages model versions, API quotas, audit logs, language packs, source licences and system health.

## 5. Core product concept: the Field Context Profile

Every recommendation is generated from a versioned Field Context Profile. It contains:

```text
Farm → Field polygon → location and area → season
  → soil inputs and provenance
  → current crop, variety, planting date and crop stage
  → weather and climate features
  → water source, irrigation method and farmer observations
  → fertilizer and management history
  → disease images, diagnoses and disease-risk indicators
  → historical harvest records
  → farmer objectives, budget and risk preference
```

Each value has provenance:

- `farmer_reported`: entered or selected by the farmer.
- `expert_verified`: confirmed during dataset or content validation.
- `public_api`: retrieved from a named public service.
- `model_predicted`: produced by a stored model version.
- `derived`: calculated from other values, such as polygon area or growing degree days.
- `unknown`: absent; the system must not silently impute it in user-facing advice.

## 6. Functional requirements

### 6.1 Account and onboarding

- Email/password or passwordless sign-in.
- Farmer profile: name, preferred language, country/region, units and consent preferences.
- Guided onboarding that asks only essential questions first.
- Progressive profiling: optional details can be added later.
- Consent for storing farm data and plant photographs.
- Data export and account deletion request.

### 6.2 Farm and field mapping

The map is a primary product feature, not a decorative location picker.

Required capabilities:

- Search a place on explicit submit or use a user-provided location.
- Display a free basemap using MapLibre GL JS or Leaflet.
- Use OpenStreetMap tiles where terms and usage limits permit, with visible attribution.
- Draw a field polygon by tapping vertices.
- Edit, undo, close and delete polygon vertices.
- Import GeoJSON as an optional advanced feature.
- Calculate area and perimeter using a geodesic calculation.
- Store polygon as GeoJSON in WGS84 and validate self-intersections.
- Add field name, soil zone, irrigation type and current crop.
- Display satellite or imagery basemap only where a legally usable free source is configured; do not imply that imagery measures crop health.
- Show field overlays later: weather point, public soil context, crop history and advisory events.
- Support multiple fields per farm and multiple seasons per field.

Map UX requirements:

- Full-screen mobile map with large controls.
- Optional satellite/street toggle.
- Manual location entry when GPS permission is denied.
- Area units: hectare, acre and local unit, with one canonical stored unit.
- Confirmation screen showing polygon, calculated area and coordinate precision warning.
- Attribution permanently visible in the map view.

### 6.3 Farm and soil profile

The farmer may enter:

- Soil pH and date/method of test.
- Nitrogen, phosphorus and potassium values, units and test source.
- Organic matter or organic carbon if known.
- Texture: sand, loam, clay, silt or farmer's local description.
- Drainage: poor, moderate or good.
- Salinity or electrical conductivity if a test is available.
- Previous crop and residue management.
- Tillage and sowing method.
- Fertilizer/manure history.
- Water source, irrigation method, number of available irrigation events and water constraints.

For users without a soil test, the platform offers an **unknown** option and explains that public soil-map values are coarse estimates. It may retrieve broad soil context from SoilGrids where the service is available, but public map values must never be presented as a field test.

### 6.4 Crop planning and suitability

Inputs:

- Candidate crop or “show options”.
- Variety, if known.
- Intended planting date or month.
- Current crop stage, if already planted.
- Farm area to allocate.
- Water availability and irrigation method.
- Farmer objective: food, income, low water use, low risk, rotation or market contract.
- Optional budget and labour constraints.

Outputs:

- Ranked crop list, not only one label.
- Suitability score with an explanation of soil, weather, season, water and rotation factors.
- Hard constraints: conditions that make a recommendation unsuitable or require expert review.
- Missing-data list and confidence level.
- Expected crop duration and key management milestones.
- Comparison view for two to five candidate crops.
- A “why not” explanation for low-ranked crops.

The crop model is a decision-support model. It must not be trained only on a synthetic toy table and marketed as a yield guarantee. A baseline can use the public Crop Recommendation dataset for engineering validation, but a research-quality model must be evaluated on geographically and temporally appropriate data.

### 6.5 Weather and climate context

For the field centroid, show:

- Current conditions.
- Daily forecast for up to seven or ten days, subject to the provider's free limits.
- Temperature range, precipitation probability/amount, humidity, wind and reference evapotranspiration where available.
- Historical seasonal summaries for model features.
- Heat, frost, heavy-rain and dry-spell alerts using transparent thresholds.
- Data timestamp, provider and forecast uncertainty.

Weather is refreshed server-side and cached. The app must degrade gracefully if the provider is unavailable by showing the last successful retrieval and its age.

### 6.6 Crop-stage and yield forecasting

The farmer records planting date, variety and current stage. The platform derives stage windows and aggregates weather into stage-aware features where the model supports them.

Yield forecast output:

- Predicted yield per hectare and total field estimate.
- Prediction interval, not just a single number.
- Forecast horizon: pre-season, early-season, mid-season or near-harvest.
- Top contributing factors using SHAP or model-specific explanations.
- Scenario comparison, such as normal rainfall versus a dry forecast.
- Explicit statement that the forecast is not a guarantee.

Minimum viable model approach:

- Baseline: crop-specific mean and linear regression.
- Tabular benchmark: Random Forest and gradient boosting/XGBoost or LightGBM.
- Optional temporal model only after enough sequential data exists.
- Time-based and location-aware validation; random row splitting alone is insufficient.

The yield module is initially limited to crops and regions for which labelled yield data exists. If no validated model is available, the UI must say “forecast unavailable for this crop/region” rather than extrapolate silently.

### 6.7 Irrigation decision support without hardware

The product provides an **irrigation planning assistant**, not sensor-driven irrigation automation.

Farmer-entered variables:

- Last irrigation date and approximate quantity/duration.
- Irrigation method: rainfed, flood, furrow, sprinkler, drip or other.
- Water source and estimated availability.
- Soil texture and drainage.
- Farmer observation: dry, normal, wet, standing water or unknown.
- Crop and growth stage.
- Optional manual soil-moisture reading from a non-connected meter.

Derived/public variables:

- Forecast rain.
- Reference evapotranspiration where available.
- Temperature, wind and humidity.
- Crop coefficient by crop and stage from approved agronomic content.

Output:

- Suggested review window, not an automatic command.
- Qualitative need: no irrigation review, monitor, likely irrigation need or urgent field check.
- Optional approximate water depth/range only when crop, soil, stage and water assumptions are known.
- Reasoning: “no rain forecast”, “high evaporative demand”, “farmer reported dry soil”, etc.
- Follow-up question when the result is unsafe due to missing information.

The system must never display a public weather/API soil-moisture value as actual moisture in the farmer's field. If a remote estimate is used in research, it must be labelled “modelled environmental estimate”.

### 6.8 Fertilizer and nutrient recommendations

Inputs include soil test values, crop, target yield if known, field area, previous crop, organic amendments, fertilizer already applied, local product names and budget.

Outputs:

- Nutrient status: deficient, likely adequate, uncertain or not assessed.
- Recommendation in nutrient units first, then product quantity only if product analysis is provided.
- Split-application schedule aligned to crop stage.
- Organic matter and non-chemical options where appropriate.
- Reasons and source citations.
- Safety warning to follow local extension guidance and product labels.

The LLM must not invent a fertilizer rate. A deterministic nutrient calculation and an approved crop knowledge record must supply the numeric basis. If a soil test is absent, the answer remains qualitative or requests a test.

### 6.9 Disease identification from images

Workflow:

1. Farmer selects crop and field, then uploads or captures one to three images.
2. The app gives capture guidance: focus, natural light, include the whole plant and close symptom view.
3. Image is resized and scanned for quality and likely leaf/plant presence.
4. A trained image model returns top-k crop/disease hypotheses and probabilities.
5. A contextual disease-risk layer combines crop, stage, recent weather and farmer observations when available.
6. The assistant explains likely symptoms and safe next steps from approved sources.
7. Low-confidence or high-risk cases are marked “needs expert confirmation”.
8. Optional expert feedback can be recorded as a separate validation record; it never overwrites the original prediction.

Initial model:

- Transfer learning with MobileNetV3, EfficientNet or ResNet using PlantVillage.
- Include healthy classes.
- Evaluate on a held-out field-style dataset where possible.
- Use calibration, top-k accuracy, macro F1 and a reject/unknown class.
- Do not expose the high laboratory accuracy of PlantVillage as field accuracy.

The referenced `shukur-alom/leaf-diseases-detect` repository may be used for code exploration, but its licence, data provenance, model quality and maintenance status must be audited before copying code or weights. The product should use the official PlantVillage source and dataset terms, not an unverified mirror.

### 6.10 Local-language agricultural assistant

The assistant supports text-first interaction and may later support speech-to-text. The farmer chooses a preferred language; responses use simple language, short steps, local units and crop names familiar to the region.

The assistant can:

- Explain the farm dashboard.
- Answer crop, soil, disease, weather, irrigation and fertilizer questions.
- Summarise the current field context.
- Explain an ML prediction and its limitations.
- Create a task plan for the next seven days.
- Convert units.
- Ask for missing information.
- Cite retrieved sources and show source dates.
- Mark the case for expert follow-up outside the automated recommendation.

The assistant cannot:

- Override hard agronomic constraints.
- Diagnose a disease with certainty from a low-quality image.
- Recommend restricted pesticide use without approved local label information.
- Make up a source, test result, weather observation or sensor reading.

### 6.11 Personalized farm reports

Reports are generated as HTML/PDF and can be shared through a downloadable file. A report includes:

- Farm and field map, area and season.
- Data provenance and completeness score.
- Current crop and stage.
- Weather summary and alerts.
- Suitability or yield forecast with uncertainty.
- Irrigation review plan.
- Fertilizer/nutrient plan.
- Disease observations and image history.
- Seven-day action checklist.
- Questions requiring expert follow-up.
- Model versions, source citations and report timestamp.

Reports must be understandable without a dashboard and must show “advisory estimate” wherever applicable.

### 6.12 Tasks, observations and feedback

- Add a dated observation: crop stage, weeds, pests, disease symptoms, soil appearance, irrigation, fertilizer or harvest.
- Create reminders from recommendations.
- Mark recommendation followed, ignored, changed or unknown.
- Record actual harvest and input usage.
- Capture farmer feedback and outcome rating.
- Allow the farmer to add notes and attach supporting evidence.

This feedback creates the product's future validation dataset only when the user has consented. It must not be silently used to retrain a production model.

## 7. Recommendation engine design

### 7.1 Pipeline

```text
User input + field polygon
        ↓
Validation, units, provenance and missing-data check
        ↓
Weather/geocoding/public-soil retrieval with caching
        ↓
Feature engineering by crop, season and stage
        ↓
Specialist ML predictions
  crop suitability | yield | disease | weather risk
        ↓
CARE context fusion and constraint checks
        ↓
Evidence retrieval from approved agricultural corpus
        ↓
Groq LLM explanation and local-language rendering
        ↓
Safety/evidence checker
        ↓
Ranked advice, confidence, citations and action plan
```

### 7.2 Context fusion

The first implementation should be an interpretable weighted decision layer rather than an opaque end-to-end neural model.

Example normalised score:

```text
CARE score(crop) =
  soil_fit × w_soil
  + climate_fit × w_climate
  + season_fit × w_season
  + water_fit × w_water
  + rotation_fit × w_rotation
  + disease_risk_adjustment × w_disease
  + farmer_objective_fit × w_objective
  - uncertainty_penalty
```

Weights are configurable per region and documented. Hard constraints can veto or downgrade a result. The model output and rule score are both stored so the research team can perform ablation studies.

### 7.3 Confidence and data completeness

Every recommendation returns:

- Model confidence or calibrated probability where meaningful.
- Data completeness: complete, adequate, limited or insufficient.
- Out-of-distribution warning when inputs are outside training ranges.
- Source freshness.
- Recommendation severity: information, monitor, action or expert review.

Low confidence must reduce the specificity of the recommendation, not merely add a disclaimer after a highly specific answer.

## 8. GenAI and RAG requirements

### 8.1 Groq

Use the Groq OpenAI-compatible API from the backend only. The API key must never be sent to the browser. The model name must be configurable through environment variables because free-plan model availability and rate limits change.

Suggested initial configuration:

- General response model: a currently available Groq Llama or open-weight production model.
- Embeddings: a locally hosted sentence-transformer or another free, self-hostable embedding model, avoiding a paid embedding API.
- Vector store: PostgreSQL with pgvector, or Chroma for local development.
- Reranker: optional local model in a later phase.

Free Groq access is rate-limited. Implement request quotas, exponential backoff, response caching, short prompts, structured JSON output and a non-LLM fallback for key recommendations.

### 8.2 Knowledge corpus

The corpus should contain locally relevant and legally reusable material:

- Government extension manuals and crop calendars.
- FAO/CGIAR and public university extension documents.
- Official pesticide labels and regulatory guidance for the target region.
- Crop-stage, nutrient and irrigation reference tables with provenance.
- Curated, reviewed FAQ content in the target languages.

Each document stores title, author, publisher, date, region, crop, language, URL, licence and review status. Do not scrape copyrighted sources indiscriminately. Do not let the LLM answer a safety-critical question when retrieval returned no trusted source.

### 8.3 Prompt contract

The backend sends the LLM:

- User question.
- Selected language and reading level.
- Relevant Field Context Profile values with provenance.
- Specialist model outputs and uncertainty.
- Retrieved evidence excerpts with citation IDs.
- Safety instructions and response schema.

The LLM returns structured JSON:

```json
{
  "answer": "...",
  "actions": [{"text": "...", "timing": "...", "priority": "..."}],
  "assumptions": ["..."],
  "missing_information": ["..."],
  "risk_level": "low|medium|high|expert_review",
  "citations": ["source-id"],
  "not_a_diagnosis": true
}
```

The safety checker validates citations, required warnings, numeric ranges, prohibited claims and agreement with specialist model outputs. Failed responses are regenerated with a narrower prompt or replaced with a safe template.

## 9. Frontend requirements

### 9.1 Recommended stack

- Next.js/React and TypeScript.
- Tailwind CSS plus an accessible component library.
- MapLibre GL JS or Leaflet with a drawing plugin.
- TanStack Query for server state and cache.
- React Hook Form plus Zod for validated multi-step forms.
- Recharts or Apache ECharts for forecasts.
- PWA service worker for cached shell, recent farm data and offline observation drafts.
- i18next or equivalent for translations.

### 9.2 Main screens

1. Welcome and language selection.
2. Farm list.
3. Create farm.
4. Map field / edit field.
5. Field overview.
6. Crop planning comparison.
7. Weather and risk timeline.
8. Crop-stage and yield forecast.
9. Irrigation planner.
10. Fertilizer and nutrient plan.
11. Disease scan and image history.
12. Agricultural assistant.
13. Tasks and observations.
14. Reports.
15. Settings, sources, consent and data export.

### 9.3 Field overview layout

The field overview should show the field map and area at the top, followed by:

- Current crop/stage and data completeness.
- Today/next-seven-day weather.
- Highest priority action.
- Disease scan status.
- Irrigation review status.
- Nutrient status.
- Forecast card with uncertainty.
- Recent observations and next task.

Use cards and plain-language labels such as “Needs field check” rather than unexplained scores. Every score has an information popover.

### 9.4 Accessibility and farmer usability

- Mobile-first, touch-friendly controls.
- High contrast and readable type.
- No colour-only meaning.
- Audio read-aloud later; text must work first.
- Local units and date formats.
- Short sentences and progressive disclosure.
- Save draft on poor connectivity.
- Show last sync time.
- Avoid requiring a map search for farmers who can mark a field manually.

## 10. Backend and system architecture

### 10.1 Recommended implementation

- API: Python FastAPI for ML and data workflows.
- Database: PostgreSQL with PostGIS; pgvector for RAG.
- Background jobs: Celery/RQ with Redis, or a simple database queue for MVP.
- Object storage: local filesystem for development; S3-compatible storage in deployment.
- ML: scikit-learn, XGBoost/LightGBM where licence and environment are acceptable, PyTorch/Torchvision for disease images, MLflow or a versioned filesystem for model artefacts.
- Authentication: self-hosted JWT/OAuth provider or a free development provider.
- Frontend: Next.js/React PWA.

### 10.2 Services

- `identity-service`: users, consent and account settings.
- `farm-service`: farms, fields, GeoJSON, area and observations.
- `data-service`: geocoding, weather, public soil context, cache and provenance.
- `ml-service`: model inference, feature validation and explanations.
- `recommendation-service`: CARE fusion, constraints and recommendation versions.
- `knowledge-service`: document ingestion, chunking, embedding, retrieval and citations.
- `assistant-service`: Groq calls, structured output and safety checks.
- `report-service`: HTML/PDF report generation.
- `training-service`: offline data preparation, training, evaluation and model registry.

For an MVP these may be modules in one FastAPI application; maintain clear interfaces so they can be split later.

## 11. Free APIs and services

The implementation must use free or open-source options during development. “Free” means no paid API dependency in the MVP; providers can impose fair-use, rate and commercial-use terms. The backend must cache responses and make providers replaceable.

### 11.1 Maps and field geometry

**Recommended:** MapLibre GL JS or Leaflet (open-source client) with OpenStreetMap-compatible tiles.

- Map rendering: OpenStreetMap tiles or another openly licensed tile provider appropriate to deployment.
- Search/geocoding: Open-Meteo Geocoding for town/postcode search, or Nominatim for deliberate user-submitted lookups.
- Nominatim constraints: no autocomplete, maximum one request per second for the application, valid identification, caching and OSM attribution. Do not build a high-volume geocoding product on the public endpoint.
- Polygon calculation: Turf.js on the client, then verify with PostGIS on the server.
- Do not depend on Google Maps or Mapbox paid services for the MVP.

### 11.2 Weather

**Open-Meteo:** forecast, historical archive, climate variables, reference evapotranspiration and related weather fields. It is keyless for the relevant free use case, but its usage limits and terms of use must be checked before public release and whenever usage grows. Show “Weather data by Open-Meteo.com” and cache requests.

Possible fallback for a US-only deployment: National Weather Service API. For historical/agroclimate research: NASA POWER or ERA5/ERA5-Land downloads, respecting their terms and processing cost.

### 11.3 Soil and environmental context

- ISRIC SoilGrids: global gridded soil properties; CC BY 4.0, coarse context, fair-use limits and service availability caveats. Prefer a downloaded/self-hosted subset for repeatable research.
- FAO WaPOR: open water-productivity data and API without a token for supported regions; coverage and variables are region-dependent, not a universal live soil-moisture sensor.
- Copernicus Data Space/Sentinel data: free data access for future remote-sensing extensions, but processing and quotas are more complex than the MVP.

### 11.4 LLM

- Groq API free plan for development and demonstration, accessed only by the backend.
- Local fallback: Ollama or llama.cpp with an open model for offline development, subject to model licence and machine capacity.

### 11.5 Reports and storage

- WeasyPrint or Playwright for PDF generation.
- PostgreSQL/PostGIS and pgvector self-hosted.
- MinIO for local S3-compatible object storage.

## 12. Data and ML plan

The project must not generate synthetic training data and must not claim that a dataset is locally representative unless it is verified.

### 12.1 Dataset manifest

Create `data/README.md` and `data/manifest.yml` listing dataset name, URL, access date, licence, task, columns/classes, geographic scope, known bias, preprocessing and citation. Store downloaded datasets outside Git or with Git LFS only when permitted.

### 12.2 Datasets to obtain

#### A. Disease classification — required for the first image model

1. **PlantVillage Dataset** — official repository `https://github.com/spMohanty/PlantVillage-Dataset` or the linked Hugging Face dataset. About 54,306 images, 14 crops and 26 diseases/healthy classes. Declared data licence is CC BY-SA 3.0 in the current dataset card; verify the exact source terms before commercial distribution. Cite Mohanty, Hughes and Salathé, 2016, DOI `10.3389/fpls.2016.01419`.
2. **DiaMOS Plant** — field-style pear images and disease monitoring dataset, 3,505 images, published 2021. Use as an external/field-style evaluation set where licence and download terms permit. DOI available from the paper page: `10.3390/agronomy11112107`.
3. Optional regional field images collected with consent and expert labels. These are valuable for domain adaptation but are not to be invented by the development team.

PlantVillage is excellent for a baseline but has controlled backgrounds. The disease model must report a domain-shift limitation and use a field-style test set whenever possible.

#### B. Crop suitability baseline

**Crop Recommendation Dataset** (commonly distributed through Kaggle/Hugging Face): N, P, K, temperature, humidity, pH, rainfall and crop label; approximately 2,200 rows and 22 crops. One source reports Apache 2.0, but the exact downloaded copy and provenance must be checked and recorded. Use only as a baseline/engineering dataset, not as proof of local suitability.

Features: `N, P, K, temperature, humidity, ph, rainfall, label`.

#### C. Yield forecasting — preferred sources

1. **FAOSTAT Crops and livestock products / production and yield** — free global annual statistics, CC BY 4.0 subject to FAO database terms. Use for country/region-level research baselines; do not imply field-level precision.
2. **USDA NASS Quick Stats** — detailed US production/yield data, with access/key requirements and terms that must be checked for the deployment use case.
3. **Historical regional or field-level records supplied by a partner** — preferred for the final research experiment. Required fields: field/region, crop, season/year, yield/unit, planting/harvest date, management, soil and weather linkage.
4. Public research datasets used in crop-yield papers, such as the datasets accompanying the 2021 interaction regression study and the 2023/2024 remote-sensing studies, if their download and licence terms allow reuse.

The project must not train a field-level yield model from national annual data and present it as a field measurement. Start with regional prediction and state the spatial resolution.

#### D. Weather, soil and remote sensing features

- Open-Meteo archive or NASA POWER for historical weather.
- SoilGrids for gridded soil properties.
- ERA5/ERA5-Land for research-scale historical weather where storage/processing is available.
- Sentinel-1/2 through Copernicus Data Space for a later remote-sensing experiment; this is optional and not required for the hardware-free MVP.

### 12.3 Model training and validation

- Data validation: schema, units, outliers, duplicates and missingness.
- Split by time and geography where possible; prevent the same field/leaf from appearing across train and test.
- Baselines must be recorded before complex models.
- Classification metrics: macro F1, balanced accuracy, per-class recall, top-k accuracy, calibration and confusion matrix.
- Regression metrics: MAE, RMSE, R², MAPE only when zero values are handled, prediction interval coverage and calibration.
- Recommendation metrics: top-1/top-3 suitability, NDCG, constraint violation rate, expert agreement and usefulness rating.
- Robustness: missing soil values, weather provider failure, out-of-range input, low-quality image and language variation.
- Explainability: SHAP for tabular models, Grad-CAM or equivalent for images, feature provenance and plain-language explanation.
- Model card: intended use, training data, exclusions, metrics, known failure modes, licence and version.

## 13. API contract

All user endpoints require authentication except health checks. Use versioned paths: `/api/v1`.

### 13.1 Core endpoints

```text
POST   /auth/register
POST   /auth/login
GET    /me

GET    /farms
POST   /farms
GET    /farms/{farm_id}
POST   /farms/{farm_id}/fields
GET    /fields/{field_id}
PATCH  /fields/{field_id}
DELETE /fields/{field_id}
POST   /fields/{field_id}/observations
GET    /fields/{field_id}/timeline

POST   /locations/geocode
GET    /fields/{field_id}/weather
GET    /fields/{field_id}/soil-context

POST   /fields/{field_id}/crop-suitability
POST   /fields/{field_id}/yield-forecast
POST   /fields/{field_id}/irrigation-plan
POST   /fields/{field_id}/fertilizer-plan
POST   /fields/{field_id}/disease-scans
GET    /disease-scans/{scan_id}

POST   /assistant/chat
GET    /assistant/conversations/{conversation_id}
POST   /reports
GET    /reports/{report_id}

GET    /sources
POST   /feedback/recommendations/{recommendation_id}
```

### 13.2 Example crop recommendation request

```json
{
  "field_id": "uuid",
  "season": "2027-kharif",
  "planting_date": "2027-06-15",
  "candidate_crops": ["rice", "maize", "pigeon_pea"],
  "soil": {
    "ph": {"value": 6.4, "source": "farmer_reported"},
    "nitrogen": {"value": 48, "unit": "mg/kg", "source": "expert_verified"},
    "texture": {"value": "loam", "source": "farmer_reported"}
  },
  "water": {
    "method": "rainfed",
    "availability": "limited",
    "source": "farmer_reported"
  },
  "objective": "low_water_risk"
}
```

### 13.3 Example recommendation response

```json
{
  "recommendation_id": "uuid",
  "ranked_options": [
    {
      "crop": "maize",
      "score": 0.78,
      "confidence": "medium",
      "reasons": ["soil pH is compatible", "rainfall forecast is adequate", "limited water lowers rice suitability"],
      "risks": ["dry spell during flowering"],
      "missing_information": ["verified phosphorus test"],
      "citations": ["crop-guide-001"]
    }
  ],
  "data_completeness": "limited",
  "model_version": "crop-context-v0.1.0",
  "generated_at": "2026-11-03T00:00:00Z"
}
```

## 14. Data model

Core tables:

- `users`, `consents`.
- `farms`, `fields`, `field_seasons`.
- `soil_profiles`, `water_profiles`, `crop_records`, `observations`.
- `weather_snapshots`, `soil_context_snapshots`, `data_sources`.
- `disease_scans`, `disease_predictions`, `expert_reviews`.
- `recommendations`, `recommendation_factors`, `recommendation_feedback`.
- `yield_records`, `yield_forecasts`.
- `knowledge_documents`, `knowledge_chunks`, `knowledge_citations`.
- `assistant_conversations`, `assistant_messages`.
- `tasks`, `reports`, `model_versions`, `audit_events`.

All user-created records contain `user_id`, `created_by`, `created_at`, `updated_at` and a provenance/audit reference where relevant. Store polygons in PostGIS with a spatial index. Store images in object storage with a database record, content hash, consent status and retention policy.

## 15. Safety, privacy and trust

- Explicitly label estimates, public data, user input and predictions.
- Never claim a diagnosis is certain from an image.
- Provide expert-review escalation for high-risk or low-confidence cases.
- Pesticide recommendations must be region-specific, label-grounded and reviewed; MVP can provide non-chemical and scouting guidance only.
- Do not store a farmer's exact location unless needed for the service; protect it as sensitive operational data.
- User-level isolation in every query and authorisation check.
- Encrypt secrets and private images in transit and at rest.
- Allow deletion/export of user data.
- Log model version, prompt template version, retrieved sources and response validation result.
- Rate-limit Groq and all public APIs.
- Use safe defaults when weather, geocoding or model services fail.
- Make the service's limitations visible in onboarding and reports.

## 16. Free project and usage model

Dhartisense will be completely free to use for farmers during the current project. There are no subscription plans, paid tiers, billing features, organisation accounts or monetisation features in the planned release.

The project should use free APIs and open-source components wherever possible. External services still have fair-use limits and usage policies, particularly public map tiles, Nominatim, Open-Meteo, datasets and PlantVillage's share-alike terms. These terms must be followed even though the application itself is free. Provider adapters should make it possible to switch to self-hosted or alternative free services if a public endpoint becomes unavailable.

## 17. MVP scope and roadmap

### Phase 0 — evidence and setup

- Confirm target country, first language, first three crops and target users.
- Obtain datasets and record licences in the manifest.
- Create repository, environment files, database schema and source-citation policy.
- Define the initial agronomy review panel.

### Phase 1 — usable hardware-free MVP

- Authentication, farm and field creation.
- Map drawing, area calculation and GeoJSON storage.
- Farmer soil/water/crop profile.
- Open-Meteo weather integration with caching.
- Crop recommendation baseline with transparent score.
- Groq assistant grounded in a small reviewed corpus.
- Basic seven-day irrigation review using farmer observations and weather.
- PDF farm report.

### Phase 2 — trained ML modules

- PlantVillage disease baseline and confidence/reject handling.
- Crop suitability benchmark and model card.
- Yield model for one crop and one data-supported region.
- SHAP/Grad-CAM explanations.
- Expert-validation record and farmer feedback capture.

### Phase 3 — context-aware engine and research evaluation

- CARE fusion with context ablations.
- Disease risk adjustment from weather/crop stage.
- Stage-aware fertilizer and irrigation rules.
- Local-language evaluation.
- Expert and farmer usability study.
- Comparison against isolated models and generic LLM advice.

### Phase 4 — scale and optional extensions

- More regional crops and languages.
- Offline-first sync improvements.
- Satellite-derived seasonal indicators where legally and technically feasible.
- Partner-provided yield data.
- Voice interface.
- Self-hosted or alternative free replacements if public API limits are reached.

## 18. Research contribution and paper plan

### Proposed paper title

**CARE: A Context-Aware Agricultural Recommendation Engine for Hardware-Free, Explainable and Local-Language Farm Advisory**

### Research question

Does a context-aware fusion of farmer-reported soil/water/management data, field location, public weather, crop stage, disease evidence and historical yield outperform isolated prediction models and generic LLM advice in recommendation quality, factuality, usefulness and safety?

### Hypotheses

- H1: CARE has higher expert-rated suitability than a crop-only classifier.
- H2: CARE has fewer agronomic constraint violations than generic LLM advice.
- H3: Retrieval grounding and specialist-model outputs improve answer citation correctness and reduce unsupported claims.
- H4: Field-style disease evaluation is substantially lower than laboratory-style evaluation, demonstrating why contextual confidence and expert escalation are necessary.
- H5: Context completeness is positively associated with recommendation usefulness, but the system retains safe behaviour under missing inputs.

### Experimental arms

1. Generic crop classifier using soil/weather features.
2. Crop classifier plus simple agronomic rules.
3. Generic Groq LLM with a user prompt and no structured context.
4. Groq + RAG with field context but no specialist model outputs.
5. Full CARE: specialist predictions + rules + RAG + safety checker.

### Ablation conditions

- Remove soil.
- Remove weather.
- Remove season/crop stage.
- Remove disease risk.
- Remove historical yield.
- Remove farmer objective/water availability.
- Remove retrieval.
- Remove safety checker.

### Evaluation dataset and protocol

- Build a benchmark of realistic field cases from public data and consented partner records; do not fabricate labels.
- Use expert agronomists to label suitable crops, unsafe advice, disease confirmation and recommendation usefulness.
- Use a time/geography-held-out test set.
- Report confidence intervals and statistical tests, not only one accuracy number.
- Measure latency, Groq rate-limit failures and missing-data behaviour.
- Conduct a small farmer usability study using task completion, SUS or a similar validated scale, comprehension and trust calibration.

## 19. Related work, 2020–2026

The following works are suitable anchors for the paper literature review. Verify final bibliographic metadata and access dates before submission.

| Year | Work | Main contribution | Limitation relevant to Dhartisense |
|---|---|---|---|
| 2020 | Bhoj et al., *Wheat crop yield prediction using new activation functions in neural network*, Neural Computing and Applications, DOI `10.1007/s00521-020-04797-8` | Neural-network yield prediction for wheat | Focuses on a prediction model; does not provide a complete field-context advisory workflow or grounded language interface |
| 2020 | Sujatha et al., *Performance of deep learning vs machine learning in plant leaf disease detection*, Microprocessors and Microsystems, DOI `10.1016/j.micpro.2020.103615` | Compares ML/DL approaches for leaf disease detection | Image classification is separated from soil, stage, weather and action planning |
| 2021 | Lu, Tan & Jiang, *Review on Convolutional Neural Network Applied to Plant Leaf Disease Classification*, Agriculture 11(8):707, DOI `10.3390/agriculture11080707` | Reviews CNN methods, datasets and field generalisation problems | Highlights the PlantVillage laboratory-to-field performance gap; does not solve cross-module contextual decision-making |
| 2021 | Diago et al., *DiaMOS Plant: A Dataset for Diagnosis and Monitoring Plant Disease*, Agronomy 11(11):2107, DOI `10.3390/agronomy11112107` | Releases a field-style pear disease dataset and analyses dataset quality | Covers a limited crop/disease setting; diagnosis is not integrated with a farm advisory engine |
| 2021 | Kogan et al., *An interaction regression model for crop yield prediction*, PNAS/PMC article | Integrates weather, soil, management and interactions for explainable yield prediction | Strong prediction and interaction analysis, but not a farmer-facing multilingual product or multi-task recommendation engine |
| 2021 | Dhaka et al., *A Survey of Deep Convolutional Neural Networks Applied for Prediction of Plant Leaf Diseases*, Sensors 21(14):4749, DOI `10.3390/s21144749` | Surveys architectures, datasets and evaluation metrics | Survey identifies methods but does not validate a complete human-in-the-loop workflow |
| 2022 | Talukder et al., *Smart farming prediction models for precision agriculture: a comprehensive survey*, Artificial Intelligence Review, DOI `10.1007/s10462-022-10266-6` | Surveys soil, crop, yield, weather, fertilizer and irrigation prediction | Describes fragmented model families; integration, provenance and farmer usability remain open |
| 2022 | Liu et al., *Developing a Dual-Stream Deep-Learning Neural Network Model for Improving County-Level Winter Wheat Yield Estimates in China*, Remote Sensing 14(20):5280, DOI `10.3390/rs14205280` | Fuses sequential remote sensing/weather with static soil for yield | County-scale and crop-specific; assumes data pipelines not available to many smallholders and does not address advisory dialogue |
| 2023 | *Yield Prediction for Winter Wheat with Machine Learning Models Using Sentinel-1, Topography, and Weather Data*, Agriculture 13(4):813, DOI `10.3390/agriculture13040813` | Uses freely available radar, topography and weather for wheat yield | Requires remote-sensing processing and farmer production data; not a hardware-free, multi-crop advisory system |
| 2023 | Tzachor et al., *Large language models and agricultural extension services*, Nature Food, DOI `10.1038/s43016-023-00867-x` | Discusses location-specific LLM extension and human-in-the-loop safeguards | Establishes the safety need but is a perspective; does not implement CARE's measurable fusion and ablation design |
| 2023 | *GPT-4 as an Agronomist Assistant? Answering Agriculture Exams Using Large Language Models*, arXiv `2310.06225` | Evaluates LLMs, RAG and ensemble refinement on agriculture questions | Exam/question performance is not the same as field-level recommendation safety or outcome improvement |
| 2024 | *Developing automated machine learning approach for fast and robust crop yield prediction using a fusion of remote sensing, soil, and weather dataset*, Environmental Research Communications, DOI `10.1088/2515-7620/ad2d02` | AutoML fusion for field-level wheat yield and climate scenarios | Crop/region-specific and data intensive; no farmer-input-first design, local-language assistant or disease-aware action planner |
| 2024 | Al-Shammari et al., *Incorporation of mechanistic model outputs as features for data-driven models for yield prediction*, Precision Agriculture, DOI `10.1007/s11119-024-10184-3` | Combines mechanistic model outputs with ML for wheat/chickpea yield | Demonstrates value of hybrid features but does not provide an end-to-end recommendation product or LLM provenance layer |
| 2024 | Yang et al., *ShizishanGPT: An Agricultural Large Language Model Integrating Tools and Resources*, arXiv `2409.13537` | Combines RAG, knowledge graph, search and agricultural tools | Strong tool/RAG precedent, but focuses on a research assistant and specialised tools rather than field polygons, farmer-entered water data and operational recommendations |
| 2024 | Nguyen et al., *My Climate Advisor: An Application of NLP in Climate Adaptation for Agriculture*, ClimateNLP 2024, ACL Anthology | RAG QA over scientific and industry sources with domain-expert evaluation | Climate adaptation QA is not a complete crop/soil/disease/yield engine; the evaluation approach is useful for CARE |
| 2025 | *Deep learning and computer vision in plant disease detection*, Artificial Intelligence Review, DOI `10.1007/s10462-024-11100-x` | Reviews 278+ papers, models, datasets and deployment trends | Confirms field robustness, foundation models and deployment challenges; still a review rather than a validated integrated platform |
| 2025 | *Applications of AI in precision agriculture*, Discover Agriculture, DOI available from publisher | Reviews AI applications for planting, irrigation, fertilization, disease and yield | Broad survey; leaves an opportunity for a hardware-free, provenance-aware integration with user-entered observations |
| 2026 | *An Integrated AI Framework for Crop Recommendation*, Horticulturae 12(4):416 | Integrates soil images, nutrients, geospatial/climate indicators and an LLM with an agronomic suitability score | Closest related crop-recommendation direction, but differs in field-operation workflow, farmer-entered hardware-free irrigation constraints, disease-aware risk and the proposed controlled comparison against generic LLM advice |
| 2026 | *Current applications of artificial intelligence for advancing agriculture, sustainability and climate mitigation*, Discover Artificial Intelligence | Reviews multimodal AI, RAG, agents and agricultural decision support | Establishes the need for validation, local knowledge and human oversight; does not supply the CARE benchmark or implementation |

### 19.1 Research gap

The literature is rich in isolated high-performing models and broad surveys, but five gaps remain:

1. **Fragmentation gap:** crop suitability, yield, disease, irrigation and fertilizer models are usually evaluated separately rather than as a single field-level advisory decision.
2. **Context gap:** many crop recommenders use a small soil/weather table and omit field geometry, planting season, crop stage, water constraints, disease risk, farmer objective and data provenance.
3. **Hardware-access gap:** many precision-agriculture systems assume IoT, sensors, remote sensing or high-quality farm records. A robust farmer-input-first design for users without hardware is less explored.
4. **GenAI evaluation gap:** agricultural LLM work demonstrates QA or RAG capability, but fewer studies compare generic LLM advice against specialist-model-plus-rule recommendations using agronomic safety, citation correctness and expert usefulness.
5. **Deployment and trust gap:** laboratory image accuracy and benchmark classifier accuracy are often not translated into calibrated uncertainty, field-style testing, local language, expert escalation and auditable farmer workflows.

Dhartisense addresses these gaps through CARE, an explicit context-fusion layer, field mapping, provenance, uncertainty, RAG citations, safety validation, local-language output and a controlled ablation study.

## 20. Success metrics and acceptance criteria

### Product acceptance

- A farmer can create a farm and draw a valid field polygon on a mobile browser in under five minutes.
- Polygon area is displayed with a unit conversion and stored accurately.
- Weather requests are cached and show provider, timestamp and failure state.
- A recommendation cannot be generated without showing missing critical inputs.
- Every numeric recommendation has a source, rule or model reference.
- Disease scans show top predictions, confidence, image quality and expert-review path.
- Assistant answers include citations or state that trusted evidence was unavailable.
- No browser bundle contains the Groq API key.
- A user cannot access another farmer's fields.
- A report can be downloaded and understood without opening the app.

### Research success targets

Targets are hypotheses, not guaranteed outcomes:

- Full CARE improves expert-rated recommendation usefulness over the generic LLM arm.
- Full CARE reduces constraint violations and unsupported numeric claims.
- Yield model reports meaningful held-out performance with uncertainty coverage.
- Disease model reports both benchmark and field-style results.
- At least 80% of critical recommendations have traceable evidence and a stored provenance chain.
- Farmers can complete core tasks with high comprehension and calibrated trust.

## 21. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Public API limits or policy changes | Cache, rate-limit, adapter interface and self-host/download where allowed |
| Poor local dataset coverage | Limit supported crops/regions; collect consented partner data; report domain shift |
| LLM hallucination | RAG, structured output, citation validator, rules, safe templates and expert review |
| Misuse of pesticide advice | Start with scouting/non-chemical guidance; use local approved labels and review |
| Farmer enters inaccurate soil data | provenance, confidence reduction and request for a soil test or expert follow-up |
| Image model fails in field | field-style evaluation, quality gate, unknown class and human escalation |
| Forecast interpreted as guarantee | intervals, assumptions, model card and prominent uncertainty |
| Low bandwidth | PWA, image compression, drafts, cached data and delayed uploads |
| Dataset licence conflict with free distribution | maintain licence manifest; replace restricted data/model before public release |
| Scope becomes too large | launch with one region, three crops, one language and one yield model |

## 22. Initial repository and implementation layout

```text
dhartisense/
├── apps/
│   ├── web/                    # Next.js PWA
│   └── api/                    # FastAPI application
├── ml/
│   ├── crop_suitability/
│   ├── yield_forecasting/
│   ├── disease_detection/
│   ├── features/
│   └── evaluation/
├── knowledge/
│   ├── documents/              # source metadata, not unlicensed copies
│   ├── ingestion/
│   └── prompts/
├── data/
│   ├── README.md
│   ├── manifest.yml
│   ├── raw/                    # gitignored; user supplies/downloads data
│   └── processed/              # gitignored artefacts
├── infra/
│   ├── docker-compose.yml
│   └── migrations/
├── docs/
│   ├── model-cards/
│   ├── api.md
│   └── research-protocol.md
├── .env.example
└── README.md
```

## 23. Immediate next steps

1. Choose the launch geography, language and first three crops.
2. Download PlantVillage and the selected crop recommendation dataset into `data/raw/` after recording their licences; do not commit large files.
3. Obtain one permitted yield dataset and define its spatial/temporal resolution.
4. Create the PostGIS schema and implement field drawing before building recommendation screens.
5. Implement Open-Meteo and geocoding adapters with caching and attribution.
6. Build the deterministic crop suitability baseline and data-completeness UI.
7. Add Groq only after the structured recommendation response works without an LLM.
8. Train and evaluate the disease baseline with a separate field-style test set.
9. Add expert-validation records and farmer feedback before presenting disease output as actionable advice.
10. Run the CARE ablation study and use the results as the central paper contribution.

## 24. Source links and citation starting points

- Groq API and rate limits: `https://console.groq.com/docs/api-reference`, `https://console.groq.com/docs/rate-limits`
- Open-Meteo forecast/geocoding: `https://open-meteo.com/en/docs`, `https://open-meteo.com/en/docs/geocoding-api`
- Nominatim policy: `https://operations.osmfoundation.org/policies/nominatim/`
- SoilGrids access and policy: `https://rest.isric.org/`, `https://docs.isric.org/globaldata/soilgrids/soilgrids_faqs_02.html`
- FAO data terms: `https://www.fao.org/contact-us/terms/db-terms-of-use/en/`
- FAOSTAT: `https://www.fao.org/faostat/en/`
- FAO WaPOR access: `https://www.fao.org/in-action/remote-sensing-for-water-productivity/wapor-data-access/en`
- Copernicus APIs: `https://dataspace.copernicus.eu/analyse/apis`
- PlantVillage repository: `https://github.com/spMohanty/PlantVillage-Dataset`
- PlantVillage paper: Mohanty, Hughes & Salathé (2016), DOI `10.3389/fpls.2016.01419`
- DiaMOS Plant paper: DOI `10.3390/agronomy11112107`
- ShizishanGPT: `https://arxiv.org/abs/2409.13537`
- My Climate Advisor: `https://aclanthology.org/2024.climatenlp-1.3/`
- Agricultural LLM extension perspective: `https://www.nature.com/articles/s43016-023-00867-x`

**Important:** API limits, model availability, dataset licences and public-service policies can change. Before deployment or paper submission, re-check each official source and record the access date in `data/manifest.yml` and the paper bibliography.
