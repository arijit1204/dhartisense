/* Field plan: crop rows, working paths and irrigation drawn on the saved boundary.
   Pure geometry plus typical spacings. It knows nothing about slope, soil or what already stands on the field. */

// crop -> [row spacing cm, plant spacing cm, suggested irrigation]. Typical recommended spacings; local advice may differ.
const CROP_LAYOUT = {
  "Rice": [20, 15, "flood"], "Wheat": [22, 5, "sprinkler"], "Maize": [60, 20, "sprinkler"], "Sorghum (jowar)": [45, 15, "sprinkler"], "Pearl millet (bajra)": [45, 12, "sprinkler"],
  "Foxtail millet": [30, 8, "sprinkler"], "Chickpea": [30, 10, "sprinkler"], "Pigeon pea": [90, 20, "sprinkler"], "Lentil": [25, 5, "sprinkler"], "Green gram (moong)": [30, 10, "sprinkler"],
  "Black gram (urad)": [30, 10, "sprinkler"], "Cowpea": [45, 15, "sprinkler"], "Field pea": [30, 10, "sprinkler"], "Soybean": [45, 5, "sprinkler"], "Groundnut": [30, 10, "sprinkler"],
  "Mustard": [45, 15, "sprinkler"], "Sunflower": [60, 30, "sprinkler"], "Sesame": [30, 10, "sprinkler"], "Safflower": [45, 20, "sprinkler"], "Linseed": [30, 5, "sprinkler"],
  "Castor": [90, 60, "drip"], "Cotton": [90, 60, "drip"], "Sugarcane": [90, 30, "drip"], "Barley": [22, 5, "sprinkler"], "Potato": [60, 20, "sprinkler"], "Tomato": [90, 45, "drip"],
  "Onion": [15, 10, "sprinkler"], "Chilli": [60, 45, "drip"], "Brinjal (eggplant)": [75, 60, "drip"], "Okra": [60, 30, "drip"], "Cucumber": [150, 60, "drip"], "Carrot": [30, 5, "sprinkler"],
  "Spinach": [20, 5, "sprinkler"], "Radish": [30, 10, "sprinkler"], "Coriander": [30, 5, "sprinkler"], "Fenugreek": [20, 5, "sprinkler"], "Turmeric": [45, 25, "drip"], "Ginger": [40, 20, "drip"],
};
const PLAN = { headland: 3, blockWidth: 36, pathWidth: 2, sprinklerSpacing: 12, sprinklerRadius: 9, emitterSpacing: 0.4, maxRowsDrawn: 220, map: null, layer: null, source: null, crop: null };

// ---- geometry in a field frame: u runs along the field's long side (where the rows go), v across it, all in metres ----

function makeFrame(polygon, bearingDeg) {
  const [lat0, lon0] = polygon[0];
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
  const ky = 110574;
  const b = (bearingDeg * Math.PI) / 180;
  const sb = Math.sin(b);
  const cb = Math.cos(b);
  return {
    toUV: ([lat, lon]) => { const x = (lon - lon0) * kx; const y = (lat - lat0) * ky; return [x * sb + y * cb, x * cb - y * sb]; },
    toLL: ([u, v]) => [lat0 + (u * cb - v * sb) / ky, lon0 + (u * sb + v * cb) / kx],
  };
}

const signedArea = (pts) => pts.reduce((sum, p, i) => { const q = pts[(i + 1) % pts.length]; return sum + p[0] * q[1] - q[0] * p[1]; }, 0) / 2;

// Moves every edge inwards by d metres. Returns null when the shape is too small or twisted for that, and the caller then plans without a headland.
function insetPolygon(pts, d) {
  const ccw = signedArea(pts) > 0;
  const lines = pts.map((p, i) => {
    const q = pts[(i + 1) % pts.length];
    const dx = q[0] - p[0];
    const dy = q[1] - p[1];
    const len = Math.hypot(dx, dy) || 1;
    const nx = ((ccw ? -dy : dy) / len) * d;
    const ny = ((ccw ? dx : -dx) / len) * d;
    return { p: [p[0] + nx, p[1] + ny], dir: [dx, dy] };
  });
  const out = lines.map((cur, i) => {
    const prev = lines[(i + lines.length - 1) % lines.length];
    const cross = prev.dir[0] * cur.dir[1] - prev.dir[1] * cur.dir[0];
    if (Math.abs(cross) < 1e-9) return cur.p;
    const t = ((cur.p[0] - prev.p[0]) * cur.dir[1] - (cur.p[1] - prev.p[1]) * cur.dir[0]) / cross;
    const vertex = [prev.p[0] + prev.dir[0] * t, prev.p[1] + prev.dir[1] * t];
    return Math.hypot(vertex[0] - pts[i][0], vertex[1] - pts[i][1]) > 6 * d ? cur.p : vertex; // cap very sharp corners
  });
  const area = signedArea(out);
  return Math.sign(area) === Math.sign(signedArea(pts)) && Math.abs(area) > 0.3 * Math.abs(signedArea(pts)) ? out : null;
}

// Stretches of the line v = const that lie inside the polygon, as [uStart, uEnd] pairs.
function scan(poly, v) {
  const hits = [];
  poly.forEach((a, i) => {
    const b = poly[(i + 1) % poly.length];
    if ((a[1] <= v && b[1] > v) || (b[1] <= v && a[1] > v)) hits.push(a[0] + ((v - a[1]) / (b[1] - a[1])) * (b[0] - a[0]));
  });
  hits.sort((x, y) => x - y);
  const segments = [];
  for (let i = 0; i + 1 < hits.length; i += 2) segments.push([hits[i], hits[i + 1]]);
  return segments;
}

function insidePolygon(poly, [u, v]) {
  return scan(poly, v).some(([a, b]) => u >= a && u <= b);
}

// ---- the plan ----

function buildPlan(profile, cropName, irrigation, sourceUV, frame) {
  const [rowCm, plantCm] = CROP_LAYOUT[cropName] || [45, 15, "sprinkler"];
  const rowSp = rowCm / 100;
  const outer = profile.polygon.map(frame.toUV);
  const inner = insetPolygon(outer, PLAN.headland);
  const area = inner || outer;
  const us = area.map((p) => p[0]);
  const vs = area.map((p) => p[1]);
  const [uMin, uMax, vMin, vMax] = [Math.min(...us), Math.max(...us), Math.min(...vs), Math.max(...vs)];

  const pathVs = [];
  if (vMax - vMin > 1.5 * PLAN.blockWidth) for (let v = vMin + PLAN.blockWidth; v < vMax - PLAN.blockWidth / 2; v += PLAN.blockWidth) pathVs.push(v);
  const rows = [];
  for (let v = vMin + rowSp / 2; v < vMax; v += rowSp) {
    if (pathVs.some((p) => Math.abs(v - p) < PLAN.pathWidth / 2)) continue;
    scan(area, v).forEach(([a, b]) => { if (b - a > 2) rows.push({ v, a, b }); });
  }
  const rowLength = rows.reduce((sum, r) => sum + (r.b - r.a), 0);
  const plan = { outer, inner, area, rows, rowLength, pathVs, vMin, vMax, uMin, uMax, rowSp, plants: Math.round(rowLength / (plantCm / 100)), rowCm, plantCm, irrigation };

  // Water enters at the end of the field nearest the source and feeds the field along a supply line.
  const uEnd = Math.abs(sourceUV[0] - uMin) < Math.abs(sourceUV[0] - uMax) ? uMin : uMax;
  const vFeed = Math.min(vMax, Math.max(vMin, sourceUV[1]));
  plan.uEnd = uEnd;
  plan.main = [sourceUV, [uEnd, vFeed]];
  plan.mainLength = Math.hypot(sourceUV[0] - uEnd, sourceUV[1] - vFeed);
  plan.submainLength = vMax - vMin;
  const farEnd = (seg) => (uEnd === uMin ? seg[1] : seg[0]);

  if (irrigation === "sprinkler") {
    const spacing = PLAN.sprinklerSpacing;
    plan.laterals = [];
    plan.sprinklers = [];
    for (let v = vMin + spacing / 2; v < vMax; v += spacing) {
      scan(area, v).forEach(([a, b]) => {
        plan.laterals.push({ v, from: uEnd, to: farEnd([a, b]) });
        const count = Math.max(1, Math.round((b - a) / spacing));
        for (let k = 0; k < count; k += 1) plan.sprinklers.push([a + ((k + 0.5) * (b - a)) / count, v]);
      });
    }
    plan.pipeLength = plan.laterals.reduce((s, l) => s + Math.abs(l.to - l.from), 0) + plan.submainLength + plan.mainLength;
    let covered = 0;
    let total = 0;
    for (let u = uMin; u <= uMax; u += 3) for (let v = vMin; v <= vMax; v += 3) {
      if (!insidePolygon(area, [u, v])) continue;
      total += 1;
      if (plan.sprinklers.some((s) => Math.hypot(s[0] - u, s[1] - v) <= PLAN.sprinklerRadius)) covered += 1;
    }
    plan.coverage = total ? covered / total : 0;
  } else if (irrigation === "drip") {
    plan.dripLength = rowLength;
    plan.emitters = Math.round(rowLength / PLAN.emitterSpacing);
    plan.pipeLength = plan.dripLength + plan.submainLength + plan.mainLength;
  } else {
    plan.pipeLength = plan.submainLength + plan.mainLength; // supply channel only; field channels depend on slope
  }
  return plan;
}

// ---- drawing and page wiring ----

function planMapInit() {
  if (PLAN.map) return;
  PLAN.map = L.map("planMap", { zoomControl: false });
  L.control.zoom({ position: "bottomright" }).addTo(PLAN.map);
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 19, maxNativeZoom: 18, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community" }).addTo(PLAN.map);
  PLAN.layer = L.layerGroup().addTo(PLAN.map);
}

function drawPlan(plan, frame) {
  const ll = (p) => frame.toLL(p);
  PLAN.layer.clearLayers();
  const add = (layer) => layer.addTo(PLAN.layer);
  add(L.polygon(plan.outer.map(ll), { color: "#ffe066", weight: 3, fill: false, interactive: false }));
  if (plan.inner) add(L.polygon(plan.inner.map(ll), { color: "#e0b07a", weight: 2, dashArray: "6 6", fill: false, interactive: false }));
  const stride = Math.max(1, Math.ceil(plan.rows.length / PLAN.maxRowsDrawn));
  plan.rows.forEach((r, i) => { if (i % stride === 0) add(L.polyline([ll([r.a, r.v]), ll([r.b, r.v])], { color: "#8be071", weight: 1.5, opacity: 0.9, interactive: false })); });
  plan.pathVs.forEach((v) => scan(plan.area, v).forEach(([a, b]) => add(L.polyline([ll([a, v]), ll([b, v])], { color: "#d9a066", weight: 5, opacity: 0.85, interactive: false }).bindTooltip("Working path", { sticky: true }))));
  const pipe = { color: "#4aa3ff", weight: 3, opacity: 0.95 };
  add(L.polyline(plan.main.map(ll), { ...pipe, dashArray: "8 6" }).bindTooltip("Main line from your water source", { sticky: true }));
  add(L.polyline([ll([plan.uEnd, plan.vMin]), ll([plan.uEnd, plan.vMax])], { ...pipe, weight: 4 }).bindTooltip(plan.irrigation === "flood" ? "Supply channel" : "Submain", { sticky: true }));
  if (plan.irrigation === "sprinkler") {
    plan.laterals.forEach((l) => add(L.polyline([ll([l.from, l.v]), ll([l.to, l.v])], { ...pipe, weight: 2 })));
    plan.sprinklers.forEach((s) => {
      add(L.circle(ll(s), { radius: PLAN.sprinklerRadius, stroke: false, fillColor: "#7cc4ff", fillOpacity: 0.12, interactive: false }));
      add(L.circleMarker(ll(s), { radius: 3, color: "#fff", weight: 1, fillColor: "#1d7fe0", fillOpacity: 1 }).bindTooltip("Sprinkler"));
    });
  }
}

function planSummary(plan, profile, crop) {
  const fieldM2 = profile.areaHa * 10000;
  const planted = plan.rowLength * plan.rowSp;
  const rank = state.lastRank?.options?.concat(state.lastRank?.picks || []).find((o) => o.crop === crop);
  const volume = rank?.irrigation_mm ? Math.round((rank.irrigation_mm * fieldM2) / 1000) : 0;
  const cell = (label, value, hint = "") => `<div><span>${label}</span><strong>${value}</strong>${hint ? `<small>${hint}</small>` : ""}</div>`;
  const per = (n) => n.toLocaleString();
  const cells = [
    cell("Field", fmtAreaBoth(profile.areaHa)),
    cell("Planted", `${Math.round((planted / fieldM2) * 100)}% of field`, `rest is headland and working paths`),
    cell("Rows", per(plan.rows.length), `${plan.rowCm} cm apart, along the ${fmtDirection(profile.bearing).split(" · ")[1].replace("long side ", "")} side`),
    cell("Plants", `about ${per(plan.plants)}`, `${plan.plantCm} cm apart in the row`),
    cell("Working paths", plan.pathVs.length ? `${plan.pathVs.length} lane${plan.pathVs.length > 1 ? "s" : ""}` : "headland only", `${PLAN.headland} m headland ring${plan.inner ? "" : " (shape too small, none drawn)"}`),
  ];
  if (plan.irrigation === "sprinkler") cells.push(cell("Sprinklers", per(plan.sprinklers.length), `${PLAN.sprinklerSpacing} × ${PLAN.sprinklerSpacing} m grid · ${Math.round(plan.coverage * 100)}% of planted area covered`), cell("Pipe", fmtLength(plan.pipeLength), "main, submain and laterals"));
  else if (plan.irrigation === "drip") cells.push(cell("Drip line", fmtLength(plan.dripLength), `one line per row · ${per(plan.emitters)} emitters at ${PLAN.emitterSpacing * 100} cm`), cell("Pipe", fmtLength(plan.pipeLength), "main, submain and drip lines"));
  else cells.push(cell("Supply channel", fmtLength(plan.pipeLength), "to the field edge; field channels depend on your slope"));
  if (volume) cells.push(cell("Season irrigation", `about ${per(volume)} m³`, `${rank.irrigation_mm} mm over the field`));
  return cells.join("");
}

function openFieldPlan(cropName) {
  const profile = state.profile;
  const panel = document.getElementById("fieldPlanPanel");
  const feedback = document.getElementById("planFeedback");
  if (!profile?.polygon || profile.polygon.length < 3) {
    panel.hidden = false;
    feedback.textContent = "Mark and close your field boundary in My fields first, then plan again.";
    return;
  }
  if (profile.bearing == null) profile.bearing = polygonMetrics(profile.polygon).bearing; // fields saved before the shape was measured
  if (!profile.areaHa) profile.areaHa = polygonMetrics(profile.polygon).areaHa;
  PLAN.crop = cropName;
  panel.hidden = false;
  feedback.textContent = "";
  planMapInit();
  const select = document.getElementById("planIrrigation");
  const own = { Sprinkler: "sprinkler", Drip: "drip", Flood: "flood", Furrow: "flood" }[profile.irrigation];
  select.value = own || (CROP_LAYOUT[cropName] || [0, 0, "sprinkler"])[2];
  document.getElementById("planTitle").textContent = `${cropName} on ${profile.fieldName || "your field"}`;
  document.getElementById("planIrrigationNote").textContent = own ? "Taken from your field profile. You can change it here." : "Suggested for this crop, since no irrigation method is set in your field profile.";
  PLAN.source = profile.waterPoint || null;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
  window.setTimeout(() => { PLAN.map.invalidateSize(); PLAN.map.fitBounds(profile.polygon, { padding: [30, 30], maxZoom: 19 }); renderFieldPlan(); }, 250);
}

function renderFieldPlan() {
  const profile = state.profile;
  const frame = makeFrame(profile.polygon, profile.bearing);
  const irrigation = document.getElementById("planIrrigation").value;
  if (!PLAN.source) { // default: middle of the polygon's first edge, the farmer can drag it
    const mid = [(profile.polygon[0][0] + profile.polygon[1][0]) / 2, (profile.polygon[0][1] + profile.polygon[1][1]) / 2];
    PLAN.source = mid;
  }
  const plan = buildPlan(profile, PLAN.crop, irrigation, frame.toUV(PLAN.source), frame);
  drawPlan(plan, frame);
  document.getElementById("planSummary").innerHTML = planSummary(plan, profile, PLAN.crop);
  if (PLAN.pin) PLAN.map.removeLayer(PLAN.pin);
  PLAN.pin = L.marker(PLAN.source, { draggable: true, title: "Water source: drag me", icon: L.divIcon({ className: "source-pin", html: "💧", iconSize: [30, 30] }) }).addTo(PLAN.map);
  PLAN.pin.on("dragend", (event) => {
    PLAN.source = [event.target.getLatLng().lat, event.target.getLatLng().lng];
    profile.waterPoint = PLAN.source;
    if (profile.farmName) saveProfile();
    renderFieldPlan();
  });
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-plan-crop]");
  if (button) openFieldPlan(button.dataset.planCrop);
});
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("planIrrigation")?.addEventListener("change", () => state.profile?.polygon && renderFieldPlan());
  document.getElementById("printPlan")?.addEventListener("click", () => { document.body.classList.add("printing-plan"); window.print(); document.body.classList.remove("printing-plan"); });
});
