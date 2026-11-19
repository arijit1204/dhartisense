"""Run the self-checks that live at the bottom of the modules.  python scripts/run_checks.py [--online]"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFLINE = ["ml.water_plan", "ml.nutrient_plan", "app.fbstore"]
ONLINE = ["app.mailer", "app.ndvi"]  # these call the internet (DNS lookup, Sentinel-2 service)

modules = OFFLINE + (ONLINE if "--online" in sys.argv else [])
failed = []
for module in modules:
    result = subprocess.run([sys.executable, "-m", module], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    ok = result.returncode == 0
    print(("PASS" if ok else "FAIL"), module, "|", (result.stdout.strip().splitlines() or [""])[-1])
    if not ok:
        failed.append(module)
        print(result.stderr[-600:])
sys.exit(1 if failed else 0)
