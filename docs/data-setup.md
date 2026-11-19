# Data and model setup

A fresh clone does not contain the datasets or model weights (too large, and third-party licences: see [NOTICE.md](../NOTICE.md)). The web app starts without them, but some features need the files below in `ml/models/`.

| File | Needed for | How to get it |
|---|---|---|
| `crop_requirements.json` | Crop plan ranking | Download `EcoCrop_DB.csv` from <https://github.com/openclim/ecocrop> to `data/raw/ecocrop/`, then run `python ml/training/build_crop_requirements.py` |
| `regional_crops.json` | Crop plan: what farmers nearby grow (India) | Download Kaggle `abhinand05/crop-production-in-india` (needs a Kaggle account, e.g. `kagglehub`), adjust the path at the top of `ml/training/build_regional_crops.py` if needed, run it (about 10 minutes of geocoding) |
| `plant_disease_v3.pth` | local plant-photo model | Train with `ml/training/train_plant_disease_v3_colab.ipynb` in Google Colab (free GPU), then copy the file here. Optional: without it the app uses the Groq vision check only |

Check the result with `python ml/training/benchmark_crop_fit.py` (downloads weather for about 120 districts the first time).

Never commit raw datasets or weights: `.gitignore` excludes `data/raw/`, `ml/models/` and common weight formats. Weights over 100 MB cannot go to GitHub without Git LFS; the deployment bundle (`deploy/build_bundle.py --with-model`) can carry it instead.
