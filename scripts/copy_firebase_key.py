"""Copy the Firebase service-account key to the clipboard as ONE line of JSON, without printing it.  python scripts/copy_firebase_key.py

Paste it into Render as the value of FIREBASE_SERVICE_ACCOUNT_JSON. Afterwards copy something else so the key does not stay in the clipboard.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env = (ROOT / ".env").read_text(encoding="utf-8") if (ROOT / ".env").exists() else ""
match = re.search(r"^FIREBASE_SERVICE_ACCOUNT_FILE\s*=\s*[\"']?(.+?)[\"']?\s*$", env, re.M)
if not match:
    sys.exit("FIREBASE_SERVICE_ACCOUNT_FILE is not set in .env")
key = Path(match.group(1).strip())
if not key.exists():
    sys.exit(f"Key file not found: {key}")
one_line = json.dumps(json.load(open(key, encoding="utf-8")))
subprocess.run(["clip"], input=one_line.encode("utf-16le"), check=True) if sys.platform == "win32" else sys.exit("Copy it manually: print(json.dumps(...)) on this machine")
print(f"Copied {len(one_line)} characters to the clipboard (not shown). Paste it into Render now, then copy something else.")
