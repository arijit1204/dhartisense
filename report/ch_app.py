"""Appendix and references."""
import json
from pathlib import Path

crops = json.loads((Path(__file__).resolve().parent.parent / "ml" / "models" / "crop_requirements.json").read_text(encoding="utf8"))["crops"]
half = (len(crops) + 1) // 2
crop_rows = []
for i in range(half):
    a = crops[i]
    b = crops[i + half] if i + half < len(crops) else None
    crop_rows.append([a["name"], a["scientific"], b["name"] if b else "", b["scientific"] if b else ""])

BLOCKS = [
    ("h1", "APPENDIX"),
    ("h2", "A. Interface routes"),
    ("p", "{tab:routes} lists the routes of the server. Every route outside the public group needs a signed-in session, and the routes marked with a limit are rate limited per user."),
    ("tab", "routes", "Routes of the Dhartisense server",
     ["Method", "Route", "Purpose"],
     [["GET", "/api/health, /api/config", "Health check and Firebase web settings (public)"],
      ["POST", "/api/auth/check-email", "Email format and mail-domain check (public)"],
      ["POST", "/api/auth/session", "Exchange a verified Firebase ID token for a session cookie (public)"],
      ["GET", "/api/auth/me", "Current user (public, answers signed-out)"],
      ["POST", "/api/auth/logout", "End the session and revoke refresh tokens (public)"],
      ["GET, POST, PUT, DELETE", "/api/fields, /api/fields/{id}", "List, create, update and delete the user's fields"],
      ["GET", "/api/weather, /api/geocode", "Forecast for a location (60 per minute) and place search (30 per minute)"],
      ["POST", "/api/crop-rank", "Crop ranking for a field and planting date (12 per minute)"],
      ["POST", "/api/water-plan", "Irrigation schedule or season outlook (20 per minute)"],
      ["POST", "/api/nutrient-plan", "Fertiliser plan from soil-test values"],
      ["POST", "/api/ndvi", "Satellite crop-health analysis (6 per minute)"],
      ["POST", "/api/disease-scan, /api/disease-advice", "Leaf photo classification (10 per minute) and advice text for a result (20 per minute)"],
      ["POST", "/api/assistant", "Assistant question with field context (20 per minute)"]],
     [2200, 3300, 4667]),
    ("h2", "B. Configuration"),
    ("p", "Settings come from environment variables or a local `.env` file that is never committed. {tab:envvars} lists them."),
    ("tab", "envvars", "Configuration variables",
     ["Variable", "Purpose"],
     [["FIREBASE_PROJECT_ID, FIREBASE_API_KEY", "Firebase web settings; the API key is public by design"],
      ["FIREBASE_SERVICE_ACCOUNT_FILE or _JSON", "Administrator key for the server (secret; keep outside the project folder)"],
      ["GROQ_API_KEY", "Key for the assistant and the photo second opinion (secret)"],
      ["GROQ_MODEL, GROQ_VISION_MODEL", "Model names for the assistant and for photos"],
      ["DHARTISENSE_HOST, DHARTISENSE_PORT (or PORT)", "Where the server listens"],
      ["DHARTISENSE_COOKIE_SECURE", "Set to 1 when the site is served over HTTPS"],
      ["DHARTISENSE_ALLOWED_ORIGINS", "Extra site addresses allowed to send changes"],
      ["DISEASE_MODEL", "Optional path to a plant-model checkpoint (version 3 is preferred if present)"],
      ["DHARTISENSE_FIRESTORE=memory", "Development and tests only: keep fields in memory"]],
     [4300, 5867]),
    ("h2", "C. Crops covered"),
    ("p", "The crop ranking, irrigation and fertiliser engines cover the same 38 crops. {tab:crops} gives their scientific names as used to look up the EcoCrop database."),
    ("tab", "crops", "Crops covered by the engines",
     ["Crop", "Scientific name", "Crop", "Scientific name"],
     crop_rows, [2200, 2883, 2200, 2884]),
    ("h2", "D. Producing the machine-learning figures"),
    ("p", "The graphs in Chapter 5 come from the notebook `report/colab/dhartisense_report_figures.ipynb`. They are produced as follows."),
    ("num", ["Open the notebook in Google Colab and choose a T4 GPU runtime.",
             "Upload `ml/crop_fit.py`, `ml/water_plan.py`, `ml/nutrient_plan.py`, `ml/models/crop_requirements.json`, `ml/models/regional_crops.json` and, for the evaluation of the served model, `ml/models/plant_disease_v3.pth` when the notebook asks.",
             "Run the sections in order. Section A draws the engine figures, section B the crop-ranking benchmark, section C evaluates the served plant model, and the optional section D retrains the model to log the training curve.",
             "Download `report_figures.zip` and copy the images into `report/figures/colab/`.",
             "Run `python report/build_report.py` again. Yellow placeholders are replaced by the images."]),
    ("h2", "E. Self-checks"),
    ("p", "The offline self-checks run with one command and print one line per module. During this work they printed the following."),
    ("code", "python scripts/run_checks.py\nPASS ml.water_plan | water_plan self-check passed: now 0 75 mm net\nPASS ml.nutrient_plan | nutrient_plan self-check passed: {'N': 150, 'P': 45, 'K': 40} {'DAP': 98, 'Urea': 288, 'MOP': 67}\nPASS app.fbstore | fbstore field layer self-check passed"),

    ("h1", "REFERENCE"),
    ("ref_list",),
]
