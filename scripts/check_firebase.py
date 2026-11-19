"""Check the Firebase settings before starting the server:  venv/Scripts/python.exe scripts/check_firebase.py

Reads .env like the server does, then tests the service-account key, Authentication access and a Firestore write/read/delete (in a throwaway
document under _healthcheck). It changes nothing else.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import fbstore, server  # noqa: E402,F401  (server loads .env)

problems = []
config = fbstore.web_config()
for name in ("FIREBASE_PROJECT_ID", "FIREBASE_API_KEY"):
    if not __import__("os").getenv(name):
        problems.append(f"{name} is not set")
if not (__import__("os").getenv("FIREBASE_SERVICE_ACCOUNT_FILE") or __import__("os").getenv("FIREBASE_SERVICE_ACCOUNT_JSON")) and not __import__("os").getenv("FIREBASE_AUTH_EMULATOR_HOST"):
    problems.append("FIREBASE_SERVICE_ACCOUNT_FILE (or _JSON) is not set")
if problems:
    sys.exit("Fix these first:\n - " + "\n - ".join(problems))

fbstore._init()
from firebase_admin import auth  # noqa: E402

try:
    auth.list_users(max_results=1)
    print("Authentication: OK (service account can read users)")
except Exception as error:
    problems.append(f"Authentication: {error}")
try:
    uid = "_healthcheck"
    saved, error = fbstore.save_field(uid, None, {"fieldName": "check"})
    assert saved, error
    assert fbstore.list_fields(uid)
    assert fbstore.delete_field(uid, saved["id"])
    print("Firestore: OK (wrote, read and deleted a test field)")
except Exception as error:
    problems.append(f"Firestore: {error}")
print("Web config the browser will receive:", {k: v for k, v in config.items() if k != "apiKey"})
sys.exit("\n".join(problems) if problems else 0)
