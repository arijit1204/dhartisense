"""Crop health from Sentinel-2 satellite images (free, no key): NDVI for a field boundary over the last few months.

Data: Copernicus Sentinel-2 L2A (10 m pixels, a new image every ~5 days), served by Microsoft's Planetary Computer.
  - STAC search finds recent scenes over the field.
  - The data API's statistics endpoint returns NDVI = (NIR - Red) / (NIR + Red) averaged over the field polygon, plus its spread.
  - The scene classification (SCL) tells how much of THE FIELD is under cloud or cloud shadow; those scenes are not used for the trend.
The browser draws the NDVI colours itself from the same service's tile endpoint (see static/ndvi.js).
"""

import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import threading
import time
import urllib.parse
import urllib.request

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
DATA_URL = "https://planetarycomputer.microsoft.com/api/data/v1/item/statistics"
EXPRESSION = "(B08-B04)/(B08+B04)"
BAD_CLASSES = {1, 3, 8, 9, 10, 11}  # saturated, cloud shadow, cloud (medium, high, thin cirrus), snow
MIN_AREA_M2 = 1000  # a 10 m pixel is 100 m2; below this a field is only a few pixels
MAX_POINTS = 300
DAYS_BACK = 150
_cache: dict = {}
_lock = threading.Lock()


def _json(url: str, body: dict | None = None, timeout: int = 60):
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def ring_to_feature(points):
    """points: [[lat, lon], ...] -> a closed GeoJSON Polygon Feature (lon, lat order)."""
    ring = [[float(lon), float(lat)] for lat, lon in points]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}


def area_m2(points) -> float:
    lat0 = sum(p[0] for p in points) / len(points)
    kx = 111320 * math.cos(math.radians(lat0))
    xy = [(p[1] * kx, p[0] * 110574) for p in points]
    twice = sum(xy[i][0] * xy[(i + 1) % len(xy)][1] - xy[(i + 1) % len(xy)][0] * xy[i][1] for i in range(len(xy)))
    return abs(twice) / 2


def find_scenes(feature, days=DAYS_BACK, limit=14):
    end = dt.date.today()
    body = {"collections": ["sentinel-2-l2a"], "intersects": feature["geometry"], "datetime": f"{end - dt.timedelta(days=days)}T00:00:00Z/{end}T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": 60}}, "sortby": [{"field": "datetime", "direction": "desc"}], "limit": limit}
    scenes = _json(STAC_URL, body)["features"]
    seen, unique = set(), []
    for s in scenes:  # a field on a tile overlap can appear twice on one day; keep one
        day = s["properties"]["datetime"][:10]
        if day not in seen:
            seen.add(day)
            unique.append({"id": s["id"], "date": day, "scene_cloud": round(s["properties"].get("eo:cloud_cover", 0), 1)})
    return unique


def _stats(item: str, feature, assets: list[str], **extra):
    pairs = [("collection", "sentinel-2-l2a"), ("item", item)] + [("assets", a) for a in assets] + list(extra.items())
    return _json(DATA_URL + "?" + urllib.parse.urlencode(pairs), feature)["properties"]["statistics"]


def share_between(histogram, low, high):
    """Share of pixels whose value falls in [low, high), from an equal-width histogram [[counts], [edges]] (linear within a bin)."""
    counts, edges = histogram
    total = sum(counts) or 1
    inside = 0.0
    for i, count in enumerate(counts):
        a, b = edges[i], edges[i + 1]
        if b <= a:
            continue
        overlap = max(0.0, min(b, high) - max(a, low))
        inside += count * overlap / (b - a)
    return inside / total


def scene_result(scene: dict, feature) -> dict:
    out = dict(scene, usable=False)
    try:
        ndvi = _stats(scene["id"], feature, ["B04", "B08"], expression=EXPRESSION, asset_as_band="true")[EXPRESSION]
        scl = _stats(scene["id"], feature, ["SCL"], categorical="true")["SCL_b1"]
    except (OSError, ValueError, KeyError):
        out["error"] = True
        return out
    classes = dict(zip(scl["histogram"][1], scl["histogram"][0]))
    total = sum(classes.values()) or 1
    bad = sum(n for c, n in classes.items() if int(c) in BAD_CLASSES) / total
    out.update(mean=round(ndvi["mean"], 3), low=round(ndvi["min"], 3), high=round(ndvi["max"], 3), spread=round(ndvi["std"], 3), pixels=int(ndvi["count"]), bad_share=round(bad, 2),
               weak=round(share_between(ndvi["histogram"], -1, 0.3), 2), moderate=round(share_between(ndvi["histogram"], 0.3, 0.6), 2), strong=round(share_between(ndvi["histogram"], 0.6, 2), 2))
    out["usable"] = bad < 0.2 and ndvi["count"] >= 4
    return out


def health_label(mean: float) -> str:
    if mean < 0.2:
        return "Very little green cover (bare soil, or just sown)"
    if mean < 0.4:
        return "Sparse or early growth"
    if mean < 0.6:
        return "Moderate cover"
    if mean < 0.8:
        return "Healthy, dense cover"
    return "Very dense, vigorous cover"


def summarise(results: list) -> dict:
    """Latest usable reading, the change since an earlier usable one (at least 5 days before), and plain-language notes."""
    usable = [r for r in results if r["usable"]]
    if not usable:
        return {"latest": None, "notes": ["No clear image of this field in the last five months (clouds). Try again in a few days."]}
    latest = usable[0]
    earlier = next((r for r in usable[1:] if (dt.date.fromisoformat(latest["date"]) - dt.date.fromisoformat(r["date"])).days >= 5), None)
    delta = round(latest["mean"] - earlier["mean"], 3) if earlier else None
    trend = None if delta is None else "improving" if delta >= 0.05 else "declining" if delta <= -0.05 else "steady"
    notes = []
    if delta is not None and delta <= -0.10:
        notes.append(f"Greenness fell by {abs(delta):.2f} since {earlier['date']}. Walk the field to look for water stress, pests or disease. If you harvested or cut the crop, this drop is expected.")
    elif trend == "improving":
        notes.append("Greenness is rising, which is normal while a crop is growing.")
    if latest["weak"] >= 0.2 and latest["mean"] >= 0.3:
        notes.append(f"About {round(latest['weak'] * 100)}% of the field is weak (below 0.3). The red areas on the map show where to look first.")
    if latest["spread"] > 0.15:
        notes.append("Greenness varies a lot across the field. Uneven water, soil or sowing is a common cause.")
    notes.append("NDVI shows how green the field looks from space. It depends on the crop and its stage, so watch the change over time more than any single number. It does not diagnose a cause.")
    return {"latest": latest, "previous": earlier, "delta": delta, "trend": trend, "label": health_label(latest["mean"]), "notes": notes}


def analyse(points) -> dict:
    """points: [[lat, lon], ...] of the field boundary. Returns {ready, scenes, summary} or {ready False, error}."""
    try:
        points = [[float(a), float(b)] for a, b in points]
    except (TypeError, ValueError):
        return {"ready": False, "error": "The field boundary is not valid."}
    if not 3 <= len(points) <= MAX_POINTS or any(not (-90 <= a <= 90 and -180 <= b <= 180) for a, b in points):
        return {"ready": False, "error": "The field boundary is not valid."}
    if area_m2(points) < MIN_AREA_M2:
        return {"ready": False, "error": "This field is too small for satellite pixels (10 m). Fields under about 0.1 ha cannot be read reliably."}
    feature = ring_to_feature(points)
    key = hashlib.sha1(json.dumps(feature["geometry"]["coordinates"]).encode()).hexdigest()
    with _lock:
        cached = _cache.get(key)
    if cached and time.time() - cached[0] < 6 * 3600:
        return cached[1]
    try:
        scenes = find_scenes(feature)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda s: scene_result(s, feature), scenes))
    except (OSError, ValueError, KeyError):
        return {"ready": False, "error": "The satellite service is not reachable right now. Try again in a few minutes."}
    if not results:
        return {"ready": False, "error": "No recent satellite images found for this field."}
    out = {"ready": True, "scenes": results, "summary": summarise(results), "source": "Copernicus Sentinel-2 L2A via Microsoft Planetary Computer", "pixel_m": 10}
    with _lock:
        _cache[key] = (time.time(), out)
    return out


if __name__ == "__main__":
    # offline checks of the maths
    assert abs(share_between([[10, 10], [0.0, 0.5, 1.0]], 0.0, 0.5) - 0.5) < 1e-9 and abs(share_between([[10, 10], [0.0, 0.5, 1.0]], 0.25, 0.75) - 0.5) < 1e-9
    assert 9_000 < area_m2([[18.52, 73.85], [18.52, 73.851], [18.521, 73.851], [18.521, 73.85]]) < 12_000
    mk = lambda d, m, bad=0.0, weak=0.0: {"id": d, "date": d, "usable": bad < 0.2, "mean": m, "weak": weak, "spread": 0.05}  # noqa: E731
    s = summarise([mk("2026-11-10", 0.45), mk("2026-11-01", 0.62), mk("2026-10-20", 0.6)])
    assert s["trend"] == "declining" and s["delta"] == -0.17 and "fell" in s["notes"][0], s
    assert summarise([mk("2026-11-10", 0.5, bad=0.5)])["latest"] is None
    assert analyse([[1, 1], [1, 1.00001], [1.00001, 1]])["ready"] is False  # too small
    # live check (needs internet): Pune sample field
    live = analyse([[18.5200, 73.8500], [18.5200, 73.8514], [18.5209, 73.8516], [18.5210, 73.8501]])
    print("live:", live.get("ready"), len(live.get("scenes", [])), "scenes;", (live.get("summary", {}).get("latest") or {}).get("date"), live.get("summary", {}).get("label"))
    print("ndvi self-check passed")
