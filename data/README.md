# Dhartisense data directory

This directory intentionally contains no generated or synthetic training data.

## Current status

The application foundation does not require a training dataset. It provides:

- Field mapping and local farm profile storage.
- Live weather and location lookup through free public APIs.
- Farmer-entered crop, soil, water and observation context.
- A Groq agricultural assistant when `GROQ_API_KEY` is configured.

The crop suitability, yield forecasting and disease models must not be presented as trained until real labelled data has been downloaded, inspected and evaluated.

## Dataset approval required

Before downloading data, approve the following initial sources:

1. **PlantVillage** for the first disease-classification baseline: 54,306 labelled leaf images, 14 crops and 38 crop/disease or healthy classes. Source: `https://github.com/spMohanty/PlantVillage-Dataset`. The current dataset card declares CC BY-SA 3.0; verify the exact downloaded source and retain its attribution.
2. **Crop Recommendation Dataset** for an engineering baseline: N, P, K, temperature, humidity, pH, rainfall and crop label. Use only after the exact source, licence and provenance are recorded.
3. **FAOSTAT Crops and livestock products** or another approved public yield source for regional yield modelling. Source: `https://www.fao.org/faostat/en/`. The spatial resolution must be disclosed; national or regional data must not be described as field measurements.
4. Optional field-style disease evaluation data such as **DiaMOS Plant**, subject to its published access and licence terms.

No source is copied into this directory until approval is received. Downloaded files must remain outside Git or be ignored with Git LFS only when the licence permits it.

## Required manifest entry

For every approved dataset, record:

- Dataset name and direct URL.
- Access date.
- Licence and attribution text.
- Task and target label.
- Geographic and temporal scope.
- File checksum.
- Known bias and limitations.
- Preprocessing steps.
- Citation.
