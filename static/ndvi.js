/* Crop health page: Sentinel-2 NDVI for the selected field (data from /api/ndvi; colours drawn by Microsoft Planetary Computer's tile service). */

const NDVI_TILES = "https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?collection=sentinel-2-l2a&item=";
const NDVI_STYLE = "&assets=B04&assets=B08&expression=%28B08-B04%29%2F%28B08%2BB04%29&asset_as_band=true&rescale=0%2C0.9&colormap_name=rdylgn&format=png";
const ndvi = { data: null, fieldId: null, selected: null, map: null, layer: null, mask: null, outline: null, colours: true, busy: false };

const ndviLabel = (m) => (m < 0.2 ? "Very little green cover (bare soil, or just sown)" : m < 0.4 ? "Sparse or early growth" : m < 0.6 ? "Moderate cover" : m < 0.8 ? "Healthy, dense cover" : "Very dense, vigorous cover");
const ndviTone = (m) => (m < 0.3 ? "red" : m < 0.5 ? "amber" : "green");

function ndviMessage(title, text, busy = false) {
  document.getElementById("ndviLayout").hidden = true;
  const box = document.getElementById("ndviMessage");
  box.hidden = false;
  box.querySelector("strong").textContent = title;
  box.querySelector("p").textContent = text;
  box.classList.toggle("busy", busy);
  document.getElementById("ndviGoFields").hidden = busy || !String(title).includes("boundary");
}

async function openNdvi() {
  const p = state.profile;
  if (!p?.polygon || p.polygon.length < 3) {
    ndviMessage("Draw your field boundary first", "Satellite crop health needs the outline of your field. Open My fields and mark its corners.");
    return;
  }
  if (ndvi.data && ndvi.fieldId === p.id && ndvi.sig === JSON.stringify(p.polygon)) { // the same field and outline: reuse what was loaded
    document.getElementById("ndviMessage").hidden = true;
    document.getElementById("ndviLayout").hidden = false;
    drawNdvi();
    return;
  }
  loadNdvi();
}

async function loadNdvi() {
  const p = state.profile;
  if (!p?.polygon || ndvi.busy) return;
  ndvi.busy = true;
  const button = document.getElementById("ndviRefresh");
  button.disabled = true;
  ndviMessage("Reading satellite images…", "Looking at the last five months of Sentinel-2 pictures of your field. This takes about 10 to 20 seconds.", true);
  try {
    const response = await fetch("/api/ndvi", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ polygon: p.polygon }) });
    const data = await response.json();
    if (!data.ready) return ndviMessage("Crop health is not available", data.error || "Try again in a few minutes.");
    ndvi.data = data;
    ndvi.fieldId = p.id;
    ndvi.sig = JSON.stringify(p.polygon);
    ndvi.selected = data.scenes.find((s) => s.usable) || null;
    document.getElementById("ndviMessage").hidden = true;
    document.getElementById("ndviLayout").hidden = false;
    drawNdvi();
    const latest = data.summary.latest;
    if (latest) {
      const next = { at: new Date().toISOString(), date: latest.date, mean: latest.mean, trend: data.summary.trend, delta: data.summary.delta, label: data.summary.label };
      if (p.ndvi?.date !== next.date || p.ndvi?.mean !== next.mean) { p.ndvi = next; saveProfile(); }
      toast(`Crop health updated · latest clear image ${fmtDay(latest.date)}.`);
    } else toast("No clear satellite image of this field recently (clouds).", "info");
  } catch {
    ndviMessage("Could not reach the satellite service", "Check your connection and try again.");
  } finally {
    ndvi.busy = false;
    button.disabled = false;
  }
}

function ndviMap() {
  if (ndvi.map) return ndvi.map;
  ndvi.map = L.map("ndviMap", { zoomControl: false, scrollWheelZoom: false });
  L.control.zoom({ position: "bottomright" }).addTo(ndvi.map);
  L.tileLayer(TILES, { maxZoom: 19, maxNativeZoom: 18, attribution: "Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community" }).addTo(ndvi.map);
  return ndvi.map;
}

function drawNdvi() {
  const p = state.profile;
  const map = ndviMap();
  setTimeout(() => {
    map.invalidateSize();
    ndvi.outline?.remove();
    ndvi.mask?.remove();
    const field = p.polygon.map((q) => [q[0], q[1]]);
    ndvi.mask = L.polygon([[[-85, -180], [-85, 180], [85, 180], [85, -180]], field], { stroke: false, fillColor: "#0c1d17", fillOpacity: 0.55, interactive: false }).addTo(map); // dims everything outside the field
    ndvi.outline = L.polygon(field, { color: "#fff", weight: 2, fill: false, interactive: false }).addTo(map);
    map.fitBounds(field, { maxZoom: 18, padding: [24, 24] });
    showNdviScene();
  }, 60);
  renderNdviSide();
}

function showNdviScene() {
  const scene = ndvi.selected;
  const map = ndvi.map;
  ndvi.layer?.remove();
  ndvi.layer = null;
  if (scene) {
    ndvi.layer = L.tileLayer(NDVI_TILES + scene.id + NDVI_STYLE, { maxZoom: 20, maxNativeZoom: 17, opacity: ndvi.colours ? 0.88 : 0, className: "ndvi-tiles" }).addTo(map);
    ndvi.layer.setZIndex(5); // above the satellite base layer
    ndvi.mask?.bringToFront();
    ndvi.outline?.bringToFront();
  }
  document.getElementById("ndviMapDate").textContent = scene ? `Image from ${fmtDay(scene.date)}` : "No clear image";
  document.getElementById("ndviShowColours").classList.toggle("on", ndvi.colours);
  document.getElementById("ndviShowPlain").classList.toggle("on", !ndvi.colours);
}

function ndviChart(points, selected) {
  if (points.length < 2) return '<p class="muted-text">A trend needs at least two clear images.</p>';
  const W = 300, H = 120, L = 28, R = 8, T = 8, B = 22;
  const x = (i) => L + (i * (W - L - R)) / (points.length - 1);
  const y = (v) => T + (1 - Math.max(0, Math.min(1, v))) * (H - T - B);
  const grid = [0, 0.25, 0.5, 0.75, 1].map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#dfe5da" stroke-width="1" /><text x="${L - 4}" y="${y(v) + 3}" text-anchor="end" font-size="8" fill="#7b8a82">${v}</text>`).join("");
  const line = points.map((q, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(q.mean).toFixed(1)}`).join(" ");
  const dots = points.map((q, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(q.mean).toFixed(1)}" r="${q.id === selected?.id ? 5 : 3}" fill="${q.id === selected?.id ? "#173f35" : "#6aa56f"}" stroke="#fff" stroke-width="1.5"><title>${q.date}: ${q.mean}</title></circle>`).join("");
  const dayShort = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return `<svg viewBox="0 0 ${W} ${H}" class="ndvi-chart" role="img" aria-label="Greenness over time">${grid}<path d="${line}" fill="none" stroke="#6aa56f" stroke-width="2" />${dots}<text x="${L}" y="${H - 5}" font-size="8" fill="#7b8a82">${dayShort(points[0].date)}</text><text x="${W - R}" y="${H - 5}" text-anchor="end" font-size="8" fill="#7b8a82">${dayShort(points[points.length - 1].date)}</text></svg>`;
}

function renderNdviSide() {
  const d = ndvi.data;
  const scene = ndvi.selected;
  const usable = d.scenes.filter((s) => s.usable);
  const chips = d.scenes.slice(0, 10).map((s) => `<button type="button" class="ndvi-date${s.id === scene?.id ? " on" : ""}" data-scene="${s.id}" ${s.usable ? "" : "disabled"} title="${s.usable ? `NDVI ${s.mean}` : "Cloud or shadow over the field"}">${fmtDay(s.date)}${s.usable ? "" : " ☁"}</button>`).join("");
  document.getElementById("ndviDates").innerHTML = `<span class="ndvi-dates-label">Pick a date</span>${chips}`;
  const side = document.getElementById("ndviSummary");
  if (!scene) {
    side.innerHTML = `<span class="eyebrow">Crop health</span><h2>No clear image yet</h2><p class="muted-text">${escapeHtml(d.summary.notes[0])}</p>`;
    return;
  }
  const earlier = usable.find((s) => s.date < scene.date && (Date.parse(scene.date) - Date.parse(s.date)) / 86400000 >= 5);
  const delta = earlier ? Math.round((scene.mean - earlier.mean) * 1000) / 1000 : null;
  const trend = delta == null ? "" : delta >= 0.05 ? "▲ rising" : delta <= -0.05 ? "▼ falling" : "● steady";
  const pct = (v) => `${Math.round(v * 100)}%`;
  const notes = scene.id === d.summary.latest?.id ? d.summary.notes : ["This is an earlier image. Pick the newest date for today's advice.", d.summary.notes[d.summary.notes.length - 1]];
  side.innerHTML = `<span class="eyebrow">Crop health · ${fmtDay(scene.date)}</span>
    <div class="ndvi-score"><strong class="${ndviTone(scene.mean)}">${scene.mean.toFixed(2)}</strong><div><b>${escapeHtml(ndviLabel(scene.mean))}</b><span>${trend}${delta != null ? ` · ${delta > 0 ? "+" : ""}${delta.toFixed(2)} since ${fmtDay(earlier.date)}` : ""}</span></div></div>
    <div class="ndvi-split" title="Share of the field by greenness"><span class="weak" style="flex:${scene.weak}"></span><span class="mid" style="flex:${scene.moderate}"></span><span class="strong" style="flex:${scene.strong}"></span></div>
    <div class="ndvi-split-labels"><span>${pct(scene.weak)} weak</span><span>${pct(scene.moderate)} moderate</span><span>${pct(scene.strong)} strong</span></div>
    <h3>Greenness over time</h3>${ndviChart([...usable].reverse(), scene)}
    <ul class="ndvi-notes">${notes.map((n) => `<li>${escapeHtml(n)}</li>`).join("")}</ul>
    <p class="source-note"><i data-lucide="info"></i><span>${escapeHtml(d.source)}. Contains modified Copernicus Sentinel data ${new Date(scene.date).getFullYear()}. Each pixel is ${d.pixel_m} m wide; a new image comes about every 5 days and cloudy ones are skipped.</span></p>`;
  iconRefresh();
}

function bindNdvi() {
  document.getElementById("ndviRefresh").addEventListener("click", () => { ndvi.data = null; loadNdvi(); });
  document.getElementById("ndviGoFields").addEventListener("click", () => setView("fields"));
  document.getElementById("ndviShowColours").addEventListener("click", () => { ndvi.colours = true; ndvi.layer?.setOpacity(0.88); showNdviScene(); });
  document.getElementById("ndviShowPlain").addEventListener("click", () => { ndvi.colours = false; ndvi.layer?.setOpacity(0); showNdviScene(); });
  document.getElementById("ndviDates").addEventListener("click", (e) => {
    const b = e.target.closest("[data-scene]");
    if (!b || b.disabled) return;
    ndvi.selected = ndvi.data.scenes.find((s) => s.id === b.dataset.scene);
    showNdviScene();
    renderNdviSide();
  });
}
document.addEventListener("DOMContentLoaded", bindNdvi);
