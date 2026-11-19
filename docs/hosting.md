# Hosting Dhartisense

Dhartisense is one Python process serving the browser app and its API, with Firebase for accounts and data. Any host that runs a Docker container or a Python process works. `deploy/build_bundle.py` assembles a clean, secret-free bundle in `build/bundle/` with a Dockerfile and a Render blueprint.

## Choosing a host

| Host | Cost | Notes |
|---|---|---|
| **Render (free web service)** | free | Needs no code changes. 512 MB memory and 0.1 CPU, sleeps after 15 minutes without visits and takes up to a minute to wake, restarts at any time, no persistent disk (all data is in Firebase). Whether a card is needed at sign-up was not confirmed: check Render's pricing page |
| **Google Cloud Run** | free allowance, needs a billing account (card) | Same Google project as Firebase, no key file needed on the server, custom domain, no sleep-wake delay worth noting. Best for real users |
| Hugging Face Spaces | **paid** for Docker | At the time of writing the Docker and Gradio SDKs are locked behind a paid plan, so the free route is not available |

The rest of this page uses Render. For Cloud Run see the end.

## Deploy on Render

1. Build the bundle (the plant-photo model is left out by default, see "Plant-photo model" below):
```powershell
.\venv\Scripts\python.exe deploy\build_bundle.py
```
2. Create a **private** GitHub repository, for example `dhartisense-deploy` (the bundle holds derived crop data), and push the bundle to it. Use the same GitHub identity setup as for the main repository:
```powershell
cd build\bundle
git init -b main
git add -A
git commit -m "Dhartisense bundle"
git remote add origin https://github.com/YOUR_USER/dhartisense-deploy.git
git push -u origin main
```
3. On <https://render.com>: **New > Blueprint**, connect GitHub, choose `dhartisense-deploy`. Render reads `render.yaml`. When asked, fill in:
   - `FIREBASE_PROJECT_ID` and `FIREBASE_API_KEY` (same as your `.env`)
  - `FIREBASE_SERVICE_ACCOUNT_JSON`: run `.\venv\Scripts\python.exe scripts\copy_firebase_key.py`. It reads the key path from your `.env` and copies the key as one line to the clipboard without showing it. Paste it, then copy something else to clear the clipboard
   - `GROQ_API_KEY`
4. Wait for the build to finish (a few minutes). Open the address Render shows (`https://dhartisense-xxxx.onrender.com`). The first visit after a sleep takes up to a minute.
5. Firebase console > Authentication > Settings > **Authorized domains**: add that Render address.
6. Google Cloud console > APIs & Services > Credentials > your browser API key > restrict **HTTP referrers** to `https://dhartisense-xxxx.onrender.com/*` and `http://localhost:8000/*`, and restrict APIs to Identity Toolkit API and Token Service API.
7. Test: create an account (check spam for the confirmation email), add a field, run Crop plan.

To update, rebuild the bundle, copy it over the deploy repository, commit and push; Render redeploys.

## Plant-photo model

By default the bundle leaves out `plant_disease_v3.pth` and photo checks use the Groq vision model only (the app handles this). The model was trained on PlantVillage (original licence CC BY-SA 3.0, share-alike) and PlantDoc, so see NOTICE.md before publishing the weights. If you want it, run `deploy\build_bundle.py --with-model`; the image then needs PyTorch (about 1 GB), which does not fit Render's free 512 MB plan, so use a bigger instance or Cloud Run.

## Google Cloud Run (when you want a custom domain or no sleeping)

Install the Google Cloud CLI, enable billing on the Firebase project (the free allowance is large; set a budget alert), then from `build\bundle`:

```powershell
gcloud run deploy dhartisense --source . --region asia-south1 --allow-unauthenticated `
  --set-env-vars "FIREBASE_PROJECT_ID=...,FIREBASE_API_KEY=...,GROQ_MODEL=openai/gpt-oss-20b,GROQ_VISION_MODEL=qwen/qwen3.8-27b" `
  --set-secrets "GROQ_API_KEY=groq-api-key:latest"
```

On Cloud Run the server uses the service's own Google identity, so `FIREBASE_SERVICE_ACCOUNT_JSON` is not needed (grant the service account the Firebase Admin and Cloud Datastore User roles). Map your domain in Cloud Run > Manage custom domains and add it to Firebase's authorized domains.

## Production notes

- The server is single-process Python (fine for a pilot). It rate-limits each signed-in user on routes that spend free quotas (assistant, photo check, satellite, weather, search), times out stalled connections and answers 500 instead of dropping the connection on a bug.
- Free hosts may sleep and restart; all data lives in Firebase.
- Before a wider launch: add a privacy policy and terms (you store emails and field boundaries), set a Firestore backup and a Google Cloud budget alert, check the licences listed in NOTICE.md, and have a native speaker review the translations.
