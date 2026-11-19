/* Dhartisense client application. No training data or fabricated predictions are embedded here. */

const DEFAULT_MAP_CENTER = [20.5937, 78.9629];

const state = {
  user: null,
  fields: [],
  profile: null,
  map: null,
  mapPoints: [],
  mapPointLayers: [],
  mapClosed: false,
  polygonLayer: null,
  lineLayer: null,
  selectedLocation: null,
  weather: null,
};
let initialPanels = { crop: "", water: "", plant: "" };
state.drawMode = "tap";

// Any API call that comes back "not signed in" sends the farmer to the sign-in screen.
const nativeFetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  const response = await nativeFetch(...args);
  const url = String(args[0]);
  if (response.status === 401 && url.startsWith("/api/") && !url.startsWith("/api/auth/")) showAuth("Your session ended. Sign in again.");
  return response;
};

// ---- Account, fields and saving (everything lives in the signed-in farmer's account on the server) ----

const ACTIVE_KEY = "dhartisense-active-field";
let saveChain = Promise.resolve();

function setSaveState(text, kind = "") {
  const el = document.getElementById("saveState");
  if (!el) return;
  el.textContent = text;
  el.className = `save-state ${kind}`;
}

function saveProfile() {
  const p = state.profile;
  p.updatedAt = new Date().toISOString();
  renderAll();
  if (!(p.id || p.fieldName)) return; // a bare location is not worth a saved field yet
  setSaveState("Saving…", "busy");
  saveChain = saveChain.then(() => persistField(p)).catch(() => { setSaveState("Not saved", "bad"); toast("Could not reach the server. Your last change is not saved yet.", "error"); });
}

async function persistField(p) {
  const response = await fetch(p.id ? `/api/fields/${p.id}` : "/api/fields", { method: p.id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p) });
  const data = await response.json();
  if (!response.ok) {
    setSaveState("Not saved", "bad");
    toast(data.error || "Could not save the field.", "error");
    return;
  }
  setSaveState(`Saved ✓ ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`, "ok");
  p.id = data.field.id;
  if (!state.fields.includes(p)) state.fields.unshift(p);
  try { localStorage.setItem(ACTIVE_KEY, String(p.id)); } catch { /* the remembered field is a convenience */ }
  renderFieldLists();
}

function resetPerFieldViews() {
  state.weather = null;
  state.lastRank = undefined;
  state.selectedLocation = null;
  waterSel.clear();
  document.getElementById("cropResult").innerHTML = initialPanels.crop;
  document.getElementById("waterResult").innerHTML = initialPanels.water;
  document.getElementById("nutrientResult").innerHTML = "";
  document.getElementById("fieldPlanPanel").hidden = true;
}

function showFieldOnMap() {
  const p = state.profile;
  state.mapPoints = p?.polygon?.length >= 3 ? p.polygon.map((point) => [point[0], point[1]]) : [];
  state.mapClosed = state.mapPoints.length >= 3;
  if (!state.map) return;
  redrawPolygon();
  state.locationPin?.remove();
  state.locationPin = null;
  if (state.mapClosed) state.map.fitBounds(state.mapPoints, { maxZoom: 19 });
  else {
    state.map.setView(p?.location ? [p.location.lat, p.location.lon] : DEFAULT_MAP_CENTER, p?.location ? 18 : 5);
    if (p?.location) state.locationPin = L.circleMarker([p.location.lat, p.location.lon], { radius: 9, color: "#fff", weight: 3, fillColor: "#c95b3b", fillOpacity: 1, interactive: false }).addTo(state.map);
  }
}

function selectField(id) {
  state.profile = state.fields.find((f) => f.id === id) || null;
  if (state.profile) toast(`Showing ${fieldTitle(state.profile)}.`, "info");
  try { localStorage.setItem(ACTIVE_KEY, String(id)); } catch { /* convenience only */ }
  resetPerFieldViews();
  showFieldOnMap();
  renderAll();
  renderFieldLists();
  if (state.profile?.location) fetchWeather();
}

function startNewField() {
  state.profile = null;
  resetPerFieldViews();
  showFieldOnMap();
  renderAll();
  renderFieldLists();
  openModal();
}

async function deleteField(id) {
  const field = state.fields.find((f) => f.id === id);
  if (!field || !window.confirm(`Delete "${fieldTitle(field)}"? Its map, soil details and plans will be removed from your account.`)) return;
  const response = await fetch(`/api/fields/${id}`, { method: "DELETE" });
  if (!response.ok) return;
  state.fields = state.fields.filter((f) => f.id !== id);
  toast(`“${fieldTitle(field)}” deleted.`, "info");
  if (state.profile?.id === id) selectField(state.fields[0]?.id);
  else renderFieldLists();
}

function waterSummary(p) {
  const wp = p?.waterPlan;
  const next = irrigationEvents(wp?.items)[0];
  const hold = (wp?.items || []).find((x) => x.status === "wait_rain");
  if (!next && !hold) return { title: "Not planned", note: wp ? "No irrigation due. Refresh on the Water page" : "Make a schedule on the Water page" };
  const age = Math.round((Date.now() - new Date(wp.at)) / 86400000);
  const stale = age >= 2 ? " · update on Water page" : "";
  if (!next || (hold && next.date > todayIso())) return { title: "Hold: rain due", note: `${hold.crop} · check the field after the rain${stale}` };
  const expected = next.label === "Expected irrigation";
  const days = Math.round((Date.parse(`${next.date}T00:00:00Z`) - Date.parse(`${todayIso()}T00:00:00Z`)) / 86400000);
  return { title: days === 0 ? "Today" : fmtDay(next.date), note: `${next.crop}${next.mm ? ` · about ${next.mm} mm` : ""}${expected ? " · expected" : ""}${days > 0 ? ` · in ${days} day${days > 1 ? "s" : ""}` : ""}${stale}`, event: next };
}

function renderFieldLists() {
  const switcher = document.getElementById("fieldSwitcher");
  if (!switcher) return;
  const draft = state.profile && !state.profile.id;
  switcher.innerHTML = (draft ? '<option value="draft" selected>New field (not saved)</option>' : "") + state.fields.map((f) => `<option value="${f.id}"${state.profile?.id === f.id ? " selected" : ""}>${escapeHtml(fieldTitle(f))}</option>`).join("") + '<option value="new">＋ Add a field</option>';
  if (!state.fields.length && !draft) switcher.insertAdjacentHTML("afterbegin", '<option value="" selected disabled>No fields yet</option>');
  document.getElementById("fieldListTitle").textContent = state.fields.length ? `${state.fields.length} field${state.fields.length > 1 ? "s" : ""} on your account` : "No fields yet";
  const list = document.getElementById("fieldList");
  list.innerHTML = state.fields.length ? state.fields.map((f) => {
    const w = waterSummary(f);
    const crop = f.cropPlan?.top?.[0]?.crop || f.crop;
    const growing = growingNames(f).join(", ");
    return `<article class="field-card${state.profile?.id === f.id ? " active" : ""}" data-field="${f.id}"><div class="field-card-head"><div><strong>${escapeHtml(fieldTitle(f))}</strong><span>${escapeHtml(f.location?.name?.split(",")[0] || "No location")} · ${formatArea(f.areaHa)}</span></div><span class="status-pill ${confidenceLabel(f) === "Good context" ? "green" : "neutral"}">${confidenceLabel(f)}</span></div>
      <div class="field-card-facts"><div><span>${growing ? "Growing" : "Best crop"}</span><b>${escapeHtml(growing || crop || "Not planned")}</b></div><div><span>Next irrigation</span><b>${escapeHtml(w.title)}</b></div><div><span>Crop health</span><b>${f.ndvi ? `${f.ndvi.mean.toFixed(2)} · ${escapeHtml(f.ndvi.label.split(" (")[0])}` : "Not checked"}</b></div></div>
      <div class="field-card-actions"><button class="text-button" data-field-go="fields">Edit field</button><button class="text-button" data-field-go="crop-plan">Crop plan</button><button class="text-button" data-field-go="water">Water</button><button class="icon-button danger" data-field-delete="${f.id}" aria-label="Delete field" title="Delete field"><i data-lucide="trash-2"></i></button></div></article>`;
  }).join("") : '<div class="notice-card"><div class="notice-icon"><i data-lucide="map"></i></div><div><strong>Add your first field</strong><p>Each field you add is saved to your account with its own map, crop plan and water schedule.</p></div></div>';
  iconRefresh();
}

// ---- Sign in / create account (Firebase Authentication does the accounts and sends the emails) ----

let authMode = "login";
let verifyTimer = null;

async function initFirebase() {
  const config = await (await fetch("/api/config")).json();
  if (!config.configured) return "The server has no Firebase settings yet. Add them to .env (see the README), then reload.";
  if (!window.farmAuth) return "Could not load the sign-in library. Check your internet connection and reload.";
  window.farmAuth.init(config);
  return null;
}

const AUTH_ERRORS = {
  "auth/email-already-in-use": "An account with this email already exists. Sign in instead.",
  "auth/invalid-email": "That email address does not look right.",
  "auth/weak-password": "Use a password of at least 8 characters.",
  "auth/wrong-password": "Email or password is not right.",
  "auth/user-not-found": "Email or password is not right.",
  "auth/invalid-credential": "Email or password is not right.",
  "auth/too-many-requests": "Too many attempts. Wait a few minutes, or reset your password.",
  "auth/network-request-failed": "Cannot reach the sign-in service. Check your connection.",
  "auth/user-disabled": "This account has been disabled.",
};
const authMessage = (error) => AUTH_ERRORS[error?.code] || `Something went wrong${error?.message ? ` (${String(error.message).slice(0, 80)})` : ""}. Try again.`;

function hidePassword() {
  const input = document.getElementById("authPassword");
  input.type = "password";
  const toggle = document.getElementById("pwToggle");
  toggle.classList.remove("on");
  toggle.setAttribute("aria-pressed", "false");
  toggle.setAttribute("aria-label", "Show password");
}

function setAuthMode(mode) {
  authMode = mode;
  const register = mode === "register";
  document.querySelectorAll(".auth-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.authMode === mode));
  document.getElementById("authNameRow").hidden = !register;
  document.getElementById("authForgot").hidden = register;
  document.getElementById("authTitle").textContent = register ? "Create your account" : "Welcome back";
  document.getElementById("authLead").textContent = register ? "Free for farmers. Use at least 8 characters for the password." : "Sign in to see your fields and plans.";
  document.getElementById("authSubmit").textContent = register ? "Create account" : "Sign in";
  document.getElementById("authPassword").autocomplete = register ? "new-password" : "current-password";
  document.getElementById("authError").textContent = "";
  hidePassword();
}

function showAuth(message) {
  document.body.classList.add("signed-out");
  clearInterval(verifyTimer);
  document.getElementById("verifyPanel").hidden = true;
  document.getElementById("authMain").hidden = false;
  state.user = null;
  setFeedback("authError", message || "", Boolean(message));
}

function showVerify(user) {
  document.body.classList.add("signed-out");
  document.getElementById("authMain").hidden = true;
  document.getElementById("verifyPanel").hidden = false;
  document.getElementById("verifyLead").textContent = `We sent a confirmation link to ${user?.email || "your email"}. Open it, then come back here. It can take a minute to arrive; check spam too.`;
  clearInterval(verifyTimer);
  verifyTimer = setInterval(() => checkVerified(false), 5000); // carries on by itself once the link was opened, even from another tab or phone
}

async function checkVerified(manual) {
  const user = window.farmAuth?.current();
  if (!user) return;
  try {
    await window.farmAuth.reload(user);
    if (user.emailVerified) {
      clearInterval(verifyTimer);
      await startSessionFor(user);
    } else if (manual) setFeedback("verifyMessage", "Not confirmed yet. Open the link in the email first.", true);
  } catch { /* try again on the next tick */ }
}

// Trade the fresh Firebase sign-in for the server's session cookie, then open the app.
async function startSessionFor(user) {
  const idToken = await window.farmAuth.idToken(user);
  const response = await fetch("/api/auth/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ idToken }) });
  const data = await response.json();
  if (response.ok) {
    document.getElementById("verifyPanel").hidden = true;
    document.getElementById("authMain").hidden = false;
    toast(`Signed in. Welcome, ${data.user.name}.`);
    return enterApp(data.user);
  }
  if (data.code === "unverified") return showVerify(user);
  showAuth(data.error || "Could not sign in.");
}

async function submitAuth(event) {
  event.preventDefault();
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const name = document.getElementById("authName").value.trim();
  const register = authMode === "register";
  if (!email || !password || (register && !name)) return setFeedback("authError", register ? "Enter your name, email and a password." : "Enter your email and password.", true);
  if (!window.farmAuth) return setFeedback("authError", "Sign-in is not available. Reload the page.", true);
  const button = document.getElementById("authSubmit");
  button.disabled = true;
  setFeedback("authError", "");
  try {
    if (register) {
      const check = await (await fetch("/api/auth/check-email", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) })).json();
      if (!check.ok) return setFeedback("authError", check.error, true);
      const user = await window.farmAuth.register(email, password, name);
      document.getElementById("authPassword").value = "";
      toast("Account created. Open the confirmation link we emailed you.");
      return showVerify(user);
    }
    const user = await window.farmAuth.login(email, password);
    document.getElementById("authPassword").value = "";
    if (!user.emailVerified) return showVerify(user);
    await startSessionFor(user);
  } catch (error) {
    setFeedback("authError", authMessage(error), true);
  } finally {
    button.disabled = false;
  }
}

async function forgotPassword() {
  const email = document.getElementById("authEmail").value.trim();
  if (!email) return setFeedback("authError", "Type your email above first, then tap Forgot password.", true);
  try {
    await window.farmAuth.sendReset(email);
    setFeedback("authError", "If an account exists for that email, a reset link is on its way.");
    toast("If that email has an account, a reset link is on its way.", "info");
  } catch (error) {
    setFeedback("authError", authMessage(error), true);
  }
}

async function resendVerification() {
  try {
    await window.farmAuth.sendVerification(window.farmAuth.current());
    setFeedback("verifyMessage", "Verification email sent.");
    toast("Verification email sent. Check your inbox and spam.");
  } catch (error) {
    setFeedback("verifyMessage", authMessage(error), true);
  }
}

async function enterApp(user) {
  state.user = user;
  CHECKS_KEY = `dhartisense.plantChecks.${user.id}`;
  const response = await fetch("/api/fields");
  state.fields = response.ok ? (await response.json()).fields : [];
  let wanted = null;
  try { wanted = localStorage.getItem(ACTIVE_KEY); } catch { /* none remembered */ }
  state.profile = state.fields.find((f) => f.id === wanted) || state.fields[0] || null;
  resetPerFieldViews();
  document.body.classList.remove("signed-out");
  document.getElementById("avatarButton").textContent = (user.name || "F").trim().charAt(0).toUpperCase();
  document.getElementById("accountLine").textContent = `Signed in as ${user.name} (${user.email})`;
  setView("overview");
  showFieldOnMap();
  renderFieldLists();
  renderAll();
  renderChecks();
  if (state.profile?.location) fetchWeather();
}

async function signOut() {
  try { await fetch("/api/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); } catch { /* the cookie expires on its own */ }
  try { await window.farmAuth?.signOut(); } catch { /* already signed out */ }
  window.location.reload();
}

async function startSession() {
  let problem = null;
  try { problem = await initFirebase(); } catch { problem = "Cannot reach the server. Check that it is running, then reload."; }
  if (problem) return showAuth(problem);
  try {
    const data = await (await fetch("/api/auth/me")).json();
    if (data.user) return await enterApp(data.user);
  } catch {
    return showAuth("Cannot reach the server. Check that it is running, then reload.");
  }
  showAuth("");
}

function iconRefresh() {
  if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
}

function openNav() {
  document.querySelector(".sidebar").classList.add("open");
  document.body.classList.add("nav-open");
  document.getElementById("mobileMenuButton")?.setAttribute("aria-expanded", "true");
}

function closeNav() {
  document.querySelector(".sidebar")?.classList.remove("open");
  document.body.classList.remove("nav-open");
  document.getElementById("mobileMenuButton")?.setAttribute("aria-expanded", "false");
}

function setView(viewName) {
  closeNav();
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === viewName);
  });
  document.querySelectorAll(".nav-item[data-view]").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });
  if (viewName === "fields") {
    window.setTimeout(() => {
      initMap();
      if (state.map) state.map.invalidateSize();
    }, 40);
  }
  if (viewName === "water") openWater();
  if (viewName === "ndvi") openNdvi();
  if (viewName === "overview" || viewName === "reports") setTimeout(() => { renderMiniMaps(); }, 80);
  window.scrollTo({ top: 0, behavior: "smooth" });
  iconRefresh();
}

function setFeedback(id, message, isError = false) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("error", isError);
}

function formatArea(areaHa) {
  if (!areaHa) return "—";
  if (useImperial()) return `${(areaHa * 2.4711).toFixed(areaHa < 4 ? 2 : 1)} ac`;
  if (areaHa < 0.01) return `${Math.round(areaHa * 10000)} m²`;
  return `${areaHa.toFixed(areaHa < 10 ? 2 : 1)} ha`;
}

function profileContext() {
  const profile = state.profile || {};
  return {
    location: profile.location?.name || "Unknown",
    crop: profile.crop || "Unknown",
    stage: profile.stage || "Unknown",
    soil: profile.texture || "Unknown",
    soilPh: profile.ph || "Unknown",
    water: profile.waterSource || "Unknown",
    irrigation: profile.irrigation || "Unknown",
    fieldArea: profile.areaHa ? `${profile.areaHa.toFixed(2)} hectares` : "Unknown",
    farmerObservation: profile.waterObservation?.soil || "No recent observation",
    language: currentLanguage(),
  };
}

function renderAll() {
  renderCropPlanInputs();
  const profile = state.profile;
  const hasProfile = Boolean(profile);
  const hasPolygon = Boolean(profile?.polygon?.length >= 3);
  const notice = document.getElementById("setupNotice");
  if (notice) notice.classList.toggle("is-hidden", hasProfile && hasPolygon);

  document.getElementById("overviewTemperature").textContent = state.weather?.data?.current?.temperature_2m != null ? tempText(state.weather.data.current.temperature_2m) : "—";
  document.getElementById("overviewWeatherLabel").textContent = state.weather?.data?.current ? weatherCodeLabel(state.weather.data.current.weather_code) : "Set a field location";
  const top = profile?.cropPlan?.top;
  const growing = growingNames(profile);
  document.getElementById("overviewCrop").textContent = growing.length ? growing.join(", ") : top?.[0]?.crop || profile?.crop || "Not set";
  document.getElementById("overviewCropNote").textContent = growing.length ? `Growing on this field · ${growing.length} crop${growing.length > 1 ? "s" : ""}` : top?.length ? `Best fit for ${new Date(profile.cropPlan.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}${top.length > 1 ? ` · then ${top.slice(1, 3).map((t) => t.crop).join(", ")}` : ""}` : profile?.crop ? "Crop you entered" : "Run Crop plan to get started";
  const water = waterSummary(profile);
  document.getElementById("overviewWater").textContent = water.title;
  document.getElementById("overviewWaterNote").textContent = water.note;
  document.getElementById("todayLabel").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  document.getElementById("overviewArea").textContent = formatArea(profile?.areaHa);
  document.getElementById("overviewFieldName").textContent = profile ? fieldTitle(profile) : "No field mapped";
  document.getElementById("summaryFieldTitle").textContent = profile ? fieldTitle(profile) : "No field profile yet";
  document.getElementById("summarySoilStatus").textContent = profile?.texture || (profile?.ph ? `pH ${profile.ph}` : "Not entered");
  document.getElementById("summaryWaterStatus").textContent = profile?.waterSource || "Not entered";
  document.getElementById("summaryCropStatus").textContent = profile?.crop || "Not entered";
  document.getElementById("topbarLocation").querySelector("span").textContent = profile?.location?.name || "Location not set";
  const step = !hasProfile ? ["Complete your field profile", "Add a field to get crop, water and fertiliser advice that fits your land.", "Getting started", "fields", "map", "Add a field"]
    : !hasPolygon ? ["Mark the field boundary", "Your basic field profile is saved. Draw the boundary to calculate area and load local weather.", "Getting started", "fields", "map", "Open field map"]
    : !profile.cropPlan ? ["Find the best crops", "Your field is mapped. Pick a planting date and see the five crops that fit it best.", "Next step", "crop-plan", "sprout", "Open crop plan"]
    : !profile.waterPlan ? ["Plan irrigation and fertiliser", `Your best crop for this field is ${profile.cropPlan.top?.[0]?.crop || "ready"}. Make its irrigation schedule and fertiliser plan.`, "Next step", "water", "droplets", "Open water and nutrients"]
    : [`Next irrigation: ${waterSummary(profile).title}`, `${waterSummary(profile).note}. Reopen the Water page to refresh it with the latest forecast.`, "Up to date", "water", "droplets", "Open water and nutrients"];
  const cal = document.getElementById("priorityCalendar");
  const nextEvent = hasPolygon && profile.waterPlan ? waterSummary(profile).event : null;
  cal.hidden = !nextEvent;
  if (nextEvent) cal.href = googleCalendarLink(nextEvent, fieldTitle(profile));
  document.getElementById("priorityTitle").textContent = step[0];
  document.getElementById("priorityText").textContent = step[1];
  document.getElementById("priorityPill").textContent = step[2];
  document.getElementById("priorityAction").innerHTML = `<i data-lucide="${step[4]}"></i> ${step[5]}`;
  document.getElementById("priorityAction").dataset.viewTarget = step[3];

  const placeholder = document.getElementById("summaryMapPlaceholder");
  placeholder.innerHTML = '<i data-lucide="map"></i><span>Map a field to see its picture here.</span>';
  placeholder.onclick = () => setView("fields");
  placeholder.style.cursor = "pointer";
  document.getElementById("summaryMap").onclick = () => setView("fields");
  renderMiniMaps();

  fillFieldForm();
  updateAssistantContext();
  renderReport();
  updateWeatherStrip();
  const nutrientValues = state.profile?.nutrients || {};
  const nutrientInputs = document.querySelectorAll(".nutrient-inputs input");
  if (nutrientInputs.length >= 3) {
    nutrientInputs[0].value = nutrientValues.N || "";
    nutrientInputs[1].value = nutrientValues.P || "";
    nutrientInputs[2].value = nutrientValues.K || "";
  }
  iconRefresh();
}

function confidenceLabel(profile) {
  if (!profile) return "Needs setup";
  const fields = [profile.location, profile.polygon, profile.crop, profile.texture, profile.waterSource].filter(Boolean).length;
  if (fields >= 5) return "Good context";
  if (fields >= 3) return "Building";
  return "Needs details";
}

function weatherCodeLabel(code) {
  if (code == null) return "Weather available";
  if (code === 0) return "Clear sky";
  if ([1, 2, 3].includes(code)) return "Partly cloudy";
  if ([45, 48].includes(code)) return "Foggy";
  if ([51, 53, 55, 56, 57].includes(code)) return "Drizzle";
  if ([61, 63, 65, 66, 67].includes(code)) return "Rain";
  if ([71, 73, 75, 77].includes(code)) return "Snow";
  if ([80, 81, 82].includes(code)) return "Rain showers";
  if ([95, 96, 99].includes(code)) return "Thunderstorm";
  return "Variable conditions";
}

function fillFieldForm() {
  const p = state.profile || {};
  ["farmName", "fieldName", "fieldCrop", "fieldStage", "soilTexture", "soilPh", "waterSource", "irrigationMethod"].forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.value = p[idMap[id]] || "";
  });
  document.getElementById("soilTestKnown").checked = Boolean(p.soilTestKnown);
}

const idMap = { farmName: "farmName", fieldName: "fieldName", fieldCrop: "crop", fieldStage: "stage", soilTexture: "texture", soilPh: "ph", waterSource: "waterSource", irrigationMethod: "irrigation" };

// ---- Field map: satellite and street layers, editable boundary, live area / perimeter / shape ----

function polygonMetrics(points) {
  const lat0 = points.reduce((sum, p) => sum + p[0], 0) / points.length;
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
  const xy = points.map((p) => [p[1] * kx, p[0] * 110574]); // metres east, north (fine for field-sized shapes)
  let twiceArea = 0;
  let perimeter = 0;
  xy.forEach((p, i) => {
    const q = xy[(i + 1) % xy.length];
    twiceArea += p[0] * q[1] - q[0] * p[1];
    perimeter += Math.hypot(q[0] - p[0], q[1] - p[1]);
  });
  // Field structure: the smallest rectangle around the shape gives its length, width and direction.
  let best = null;
  for (let deg = 0; deg < 180; deg += 1) {
    const a = (deg * Math.PI) / 180;
    const c = Math.cos(a);
    const s = Math.sin(a);
    const us = xy.map((p) => p[0] * c + p[1] * s);
    const vs = xy.map((p) => -p[0] * s + p[1] * c);
    const w = Math.max(...us) - Math.min(...us);
    const h = Math.max(...vs) - Math.min(...vs);
    if (!best || w * h < best.w * best.h) best = { w, h, deg };
  }
  const longDeg = best.w >= best.h ? best.deg : best.deg + 90;
  return { areaHa: Math.abs(twiceArea) / 2 / 10000, perimeterM: perimeter, lengthM: Math.max(best.w, best.h), widthM: Math.min(best.w, best.h), bearing: (((90 - longDeg) % 180) + 180) % 180 };
}

const fmtLength = (m) => (m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(2)} km`);
const fmtAreaBoth = (ha) => (ha < 0.01 ? `${Math.round(ha * 10000)} m²` : `${ha.toFixed(2)} ha · ${(ha * 2.4711).toFixed(2)} acres`);
const AXIS_NAMES = ["North–South", "NE–SW", "East–West", "SE–NW"];
const fmtDirection = (bearing) => `${Math.round(bearing)}° · long side ${AXIS_NAMES[Math.round((bearing % 180) / 45) % 4]}`;

function initMap() {
  if (state.map || !window.L || !document.getElementById("fieldMap")) return;
  const location = state.profile?.location;
  state.map = L.map("fieldMap", { zoomControl: false }).setView(location ? [location.lat, location.lon] : DEFAULT_MAP_CENTER, location ? 17 : 5);
  L.control.zoom({ position: "bottomright" }).addTo(state.map);
  // Esri's newer "Clarity" imagery is sharper and more recent than the classic layer in many rural areas; both are free to use with attribution.
  const sharp = L.tileLayer("https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 20, maxNativeZoom: 19, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community" });
  const classic = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 19, maxNativeZoom: 18, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community" });
  const names = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", { maxZoom: 19, attribution: "Labels &copy; Esri" });
  // Clarity has gaps in some areas, so the classic imagery sits underneath it: wherever a Clarity tile is missing, the classic one shows through.
  const underlay = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 20, maxNativeZoom: 18, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community" });
  const sharpWithFallback = L.layerGroup([underlay, sharp]);
  sharpWithFallback.addTo(state.map);
  names.addTo(state.map);
  L.control.layers({ "Satellite (sharp)": sharpWithFallback, "Satellite (classic)": classic }, { "Place names": names }, { position: "topright", collapsed: true }).addTo(state.map);
  state.map.on("click", (event) => addMapPoint(event.latlng.lat, event.latlng.lng));
  bindFreehand();
  if (state.profile?.polygon?.length >= 3) {
    state.mapPoints = state.profile.polygon.map((point) => [point[0], point[1]]);
    state.mapClosed = true;
    redrawPolygon();
    state.map.fitBounds(state.profile.polygon, { maxZoom: 18 });
  } else {
    drawShape();
  }
}

function addMapPoint(lat, lon) {
  if (!state.map || state.mapClosed || state.drawMode === "free" || state.mapPoints.length >= 200) return;
  state.mapPoints.push([lat, lon]);
  redrawPolygon();
}

function closeShape() {
  if (state.mapClosed || state.mapPoints.length < 3) {
    setFeedback("fieldFeedback", "Add at least three corners before closing the boundary.", true);
    return;
  }
  state.mapClosed = true;
  drawShape();
  commitShape();
  const area = fmtAreaBoth(polygonMetrics(state.mapPoints).areaHa);
  toast(state.profile?.id || state.profile?.fieldName ? `Boundary saved · ${area}` : `Boundary closed · ${area}. Save the field profile to keep it.`);
}

function redrawPolygon() {
  if (!state.map) return;
  state.mapPointLayers.forEach((layer) => state.map.removeLayer(layer));
  state.mapPointLayers = state.mapPoints.map((point, index) => {
    const marker = L.marker(point, { draggable: true, icon: L.divIcon({ className: `vertex${index === 0 ? " first" : ""}`, iconSize: [18, 18] }), title: index === 0 ? "First corner" : `Corner ${index + 1}` }).addTo(state.map);
    marker.on("drag", (event) => { state.mapPoints[index] = [event.latlng.lat, event.latlng.lng]; drawShape(); });
    marker.on("dragend", commitShape);
    marker.on("contextmenu", () => removeCorner(index));
    if (index === 0) marker.on("click", closeShape);
    return marker;
  });
  drawShape();
}

function drawShape() {
  if (!state.map) return;
  if (state.lineLayer) state.map.removeLayer(state.lineLayer);
  if (state.polygonLayer) state.map.removeLayer(state.polygonLayer);
  state.lineLayer = state.polygonLayer = null;
  const points = state.mapPoints;
  if (points.length >= 2 && !state.mapClosed) state.lineLayer = L.polyline(points, { color: "#ffe066", weight: 3, dashArray: "6 6" }).addTo(state.map);
  if (points.length >= 3 && state.mapClosed) {
    const m = polygonMetrics(points);
    state.polygonLayer = L.polygon(points, { color: "#ffe066", weight: 3, fillColor: "#87aa69", fillOpacity: 0.25, interactive: false })
      .bindTooltip(fmtAreaBoth(m.areaHa), { permanent: true, direction: "center", className: "area-label" }).addTo(state.map);
  }
  renderMapStats();
}

// ---- Freehand drawing for curved edges ----

function setDrawMode(mode) {
  state.drawMode = mode;
  document.getElementById("modeTap").classList.toggle("on", mode === "tap");
  document.getElementById("modeFree").classList.toggle("on", mode === "free");
  document.getElementById("fieldMap").classList.toggle("freehand-on", mode === "free");
  document.getElementById("mapHint").textContent = mode === "free"
    ? "Press and drag along the edge of your field to draw it. Lift your finger or mouse to finish; the shape closes by itself. Zoom in first for a more exact outline."
    : "Tap corners around your field, then tap the first corner to close it. For curved edges, switch to Draw freehand and trace the boundary with your finger or mouse.";
}

// Douglas-Peucker: keeps the shape of a traced line with far fewer points. Distances are in metres.
function simplifyPath(points, toleranceM) {
  const lat0 = points.reduce((sum, q) => sum + q[0], 0) / points.length;
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
  const xy = points.map((q) => [q[1] * kx, q[0] * 110574]);
  const keep = new Array(points.length).fill(false);
  // A traced loop ends where it began, so split it at the point farthest from the start and simplify each half.
  let mid = 0;
  xy.forEach((q, i) => { if (Math.hypot(q[0] - xy[0][0], q[1] - xy[0][1]) > Math.hypot(xy[mid][0] - xy[0][0], xy[mid][1] - xy[0][1])) mid = i; });
  keep[0] = keep[mid] = keep[points.length - 1] = true;
  const stack = [[0, mid], [mid, points.length - 1]];
  while (stack.length) {
    const [i, j] = stack.pop();
    let far = -1;
    let farDist = toleranceM;
    const [ax, ay] = xy[i];
    const [bx, by] = xy[j];
    const len = Math.hypot(bx - ax, by - ay) || 1e-9;
    for (let k = i + 1; k < j; k++) {
      const d = Math.abs((bx - ax) * (ay - xy[k][1]) - (ax - xy[k][0]) * (by - ay)) / len;
      if (d > farDist) { far = k; farDist = d; }
    }
    if (far >= 0) { keep[far] = true; stack.push([i, far], [far, j]); }
  }
  return points.filter((_, i) => keep[i]);
}

function finishFreehand(raw) {
  let tolerance = 1.5;
  let shape = simplifyPath(raw, tolerance);
  while (shape.length > 120) shape = simplifyPath(raw, (tolerance *= 1.5));
  if (shape.length > 3 && polygonMetrics([shape[0], shape[shape.length - 1], shape[0]]).perimeterM < 6) shape.pop(); // the stroke ended on its start: do not keep the same corner twice
  if (shape.length < 3 || polygonMetrics(shape).areaHa < 0.0005) {
    toast("That outline was too small. Draw all the way around the field in one go.", "error");
    return;
  }
  state.mapPoints = shape.map((q) => [q[0], q[1]]);
  state.mapClosed = true;
  redrawPolygon();
  commitShape();
  setDrawMode("tap");
  toast(`Boundary drawn · ${fmtAreaBoth(polygonMetrics(shape).areaHa)}. Drag a corner to fine-tune it.`);
}

function bindFreehand() {
  const box = state.map.getContainer();
  let drawing = null;
  const add = (event) => {
    const at = state.map.mouseEventToLatLng(event);
    drawing.points.push([at.lat, at.lng]);
    drawing.line.setLatLngs(drawing.points);
  };
  box.addEventListener("pointerdown", (event) => {
    if (state.drawMode !== "free" || state.mapClosed || event.button > 0 || event.target.closest(".leaflet-control")) return;
    drawing = { points: [], line: L.polyline([], { color: "#ffe066", weight: 4 }).addTo(state.map) };
    state.map.dragging.disable();
    try { box.setPointerCapture?.(event.pointerId); } catch { /* capture is only a convenience */ }
    add(event);
  });
  box.addEventListener("pointermove", (event) => { if (drawing) add(event); });
  const end = () => {
    if (!drawing) return;
    const done = drawing;
    drawing = null;
    state.map.removeLayer(done.line);
    state.map.dragging.enable();
    finishFreehand(done.points);
  };
  box.addEventListener("pointerup", end);
  box.addEventListener("pointercancel", end);
}

function renderMapStats() {
  const box = document.getElementById("mapStats");
  if (!box) return;
  const count = state.mapPoints.length;
  document.getElementById("finishPolygon").hidden = state.mapClosed || count < 3;
  document.getElementById("undoPoint").hidden = count === 0;
  document.getElementById("clearPolygon").hidden = count === 0;
  if (state.mapClosed && state.mapPoints.length >= 3) {
    const m = polygonMetrics(state.mapPoints);
    const cell = (label, value) => `<div><span>${label}</span><strong>${value}</strong></div>`;
    box.innerHTML = cell("Area", fmtAreaBoth(m.areaHa)) + cell("Perimeter", fmtLength(m.perimeterM)) + cell("Length × width", `${fmtLength(m.lengthM)} × ${fmtLength(m.widthM)}`) + cell("Direction", fmtDirection(m.bearing));
  } else {
    const n = state.mapPoints.length;
    box.innerHTML = `<p>${n ? `${n} corner${n > 1 ? "s" : ""} placed. ${n >= 3 ? "Tap the first point or the tick to close the shape." : "Add at least 3 corners."}` : "Area and perimeter appear here as you mark the corners of your field."}</p>`;
  }
}

// Writes the finished shape into the profile (and to this device when the profile already exists).
function commitShape() {
  const closed = state.mapClosed && state.mapPoints.length >= 3;
  if (state.profile) {
    const m = closed ? polygonMetrics(state.mapPoints) : null;
    Object.assign(state.profile, closed
      ? { polygon: state.mapPoints.map((p) => [p[0], p[1]]), areaHa: m.areaHa, perimeterM: m.perimeterM, lengthM: m.lengthM, widthM: m.widthM, bearing: m.bearing }
      : { polygon: null, areaHa: 0, perimeterM: 0, lengthM: 0, widthM: 0, bearing: null });
    if (state.profile.id || state.profile.fieldName) saveProfile(); else renderAll();
  }
}

function removeCorner(index) {
  if (state.mapClosed && state.mapPoints.length <= 3) return;
  state.mapPoints.splice(index, 1);
  redrawPolygon();
  commitShape();
}

function undoPoint() {
  if (!state.mapPoints.length) return;
  state.mapPoints.pop();
  state.mapClosed = false;
  redrawPolygon();
  commitShape();
}

function clearPolygon() {
  if (state.mapClosed && !window.confirm("Clear the boundary you drew?")) return;
  state.mapPoints = [];
  state.mapClosed = false;
  redrawPolygon();
  commitShape();
}

// ---- Find a place: Open-Meteo first, OpenStreetMap Nominatim for villages and landmarks it does not know ----

const INDIA_BBOX = "68.1,6.5,97.4,35.7"; // west, south, east, north

// Villages and landmarks: OpenStreetMap's Nominatim and Photon (both open source), limited to India first; then worldwide.
async function searchPlaces(query) {
  const coords = query.match(/^\s*(-?\d{1,2}(?:\.\d+)?)\s*[, ]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/); // "18.52, 73.85" pasted from a phone or Google Maps
  if (coords && Math.abs(Number(coords[1])) <= 90 && Math.abs(Number(coords[2])) <= 180) return [{ name: `${coords[1]}, ${coords[2]} (coordinates)`, lat: Number(coords[1]), lon: Number(coords[2]) }];
  const q = encodeURIComponent(query);
  const json = (url) => fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error("search failed"))));
  const [osm, photon] = await Promise.allSettled([
    json(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=6&countrycodes=in&q=${q}`),
    json(`https://photon.komoot.io/api/?q=${q}&limit=6&lang=en&bbox=${INDIA_BBOX}`),
  ]);
  const found = [];
  if (osm.status === "fulfilled") osm.value.forEach((r) => found.push({ name: r.display_name, lat: Number(r.lat), lon: Number(r.lon) }));
  if (photon.status === "fulfilled") (photon.value.features || []).forEach((f) => found.push({ name: [f.properties.name, f.properties.district || f.properties.city, f.properties.state].filter(Boolean).join(", "), lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] }));
  const seen = new Set();
  const unique = found.filter((x) => { const k = `${x.lat.toFixed(3)},${x.lon.toFixed(3)}`; if (seen.has(k)) return false; seen.add(k); return true; });
  if (unique.length) return unique.slice(0, 8);
  try {
    const payload = await json(`/api/geocode?name=${q}`);
    if (payload.results?.length) return payload.results.map((r) => ({ name: [r.name, r.admin1, r.country].filter(Boolean).join(", "), lat: r.latitude, lon: r.longitude }));
  } catch { /* fall through to a worldwide search */ }
  return (await json(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=6&q=${q}`)).map((r) => ({ name: r.display_name, lat: Number(r.lat), lon: Number(r.lon) }));
}

async function findFieldPlace() {
  const query = document.getElementById("fieldLocationQuery").value.trim();
  const results = document.getElementById("fieldLocationResults");
  if (query.length < 2) return;
  results.innerHTML = '<span class="muted-text">Searching…</span>';
  let places = [];
  try { places = await searchPlaces(query); } catch { results.innerHTML = '<span class="muted-text">Search is unavailable right now. Check your connection and try again.</span>'; return; }
  if (!places.length) { results.innerHTML = '<span class="muted-text">No place found. Try a nearby town, or use your device location.</span>'; return; }
  results.innerHTML = "";
  places.forEach((place) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "location-result";
    button.textContent = place.name;
    button.addEventListener("click", () => {
      state.selectedLocation = { name: place.name, lat: place.lat, lon: place.lon };
      if (state.profile) { state.profile.location = state.selectedLocation; if (state.profile.id || state.profile.fieldName) saveProfile(); fetchWeather(); }
      initMap();
      state.map?.setView([place.lat, place.lon], 17);
      results.innerHTML = `<span class="status-pill green">Moved to ${escapeHtml(place.name.split(",")[0])}. Mark your field on the map.</span>`;
    });
    results.appendChild(button);
  });
}

async function fetchWeather(quiet = true) {
  const location = state.profile?.location;
  if (!location) {
    if (!quiet) toast("Add a field location first, then refresh.", "info");
    return false;
  }
  try {
    const response = await fetch(`/api/weather?lat=${encodeURIComponent(location.lat)}&lon=${encodeURIComponent(location.lon)}`);
    if (!response.ok) throw new Error("weather request failed");
    state.weather = await response.json();
    renderAll();
    return true;
  } catch {
    try { // some hosts' shared addresses are refused by the free weather service, so ask it from this browser instead
      state.weather = await directWeather(location.lat, location.lon);
      renderAll();
      return true;
    } catch {
      if (!quiet) toast("Weather is not available right now. Try again in a moment.", "error");
      return false;
    }
  }
}

// Same answer as the server's /api/weather, fetched straight from Open-Meteo (it allows browser requests).
async function directWeather(lat, lon) {
  const query = new URLSearchParams({ latitude: lat, longitude: lon, timezone: "auto", forecast_days: "7", current: "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code", daily: "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,et0_fao_evapotranspiration" });
  const response = await nativeFetch(`https://api.open-meteo.com/v1/forecast?${query}`);
  if (!response.ok) throw new Error("direct weather request failed");
  return { source: "Open-Meteo", source_url: "https://open-meteo.com/", retrieved_at: new Date().toISOString(), cached: false, data: await response.json() };
}

// The top-bar refresh: reloads your fields from the account and the latest weather, and says what happened.
async function refreshAll() {
  const button = document.getElementById("refreshWeather");
  button.classList.add("loading");
  button.disabled = true;
  try {
    const response = await fetch("/api/fields");
    if (!response.ok) throw new Error("fields");
    const fresh = (await response.json()).fields;
    const activeId = state.profile?.id;
    state.fields = fresh;
    if (activeId) state.profile = fresh.find((f) => f.id === activeId) || fresh[0] || null;
    renderFieldLists();
    renderAll();
    const weatherOk = await fetchWeather(false);
    renderMiniMaps();
    if (weatherOk || !state.profile?.location) toast(`Updated just now · ${fresh.length} field${fresh.length === 1 ? "" : "s"}${weatherOk ? " and the latest weather" : ""}.`);
  } catch {
    toast("Could not refresh. Check your connection.", "error");
  } finally {
    button.classList.remove("loading");
    button.disabled = false;
  }
}

function updateWeatherStrip() {
  const strip = document.getElementById("waterWeatherStrip");
  const title = document.getElementById("waterWeatherTitle");
  if (!strip || !title) return;
  title.textContent = state.profile?.location?.name || "Location not set";
  const daily = state.weather?.data?.daily;
  if (!daily?.time?.length) {
    strip.innerHTML = '<span class="muted-text">Map a field to load public weather context.</span>';
    return;
  }
  strip.innerHTML = `<div class="weather-strip-cards">${daily.time.slice(0, 3).map((date, index) => `<div class="weather-mini"><strong>${tempText(daily.temperature_2m_max[index])}</strong><span>${new Date(date).toLocaleDateString(undefined, { weekday: "short" })} · ${Math.round(daily.precipitation_probability_max[index] || 0)}% rain</span></div>`).join("")}</div>`;
}

function updateAssistantContext() {
  const context = profileContext();
  document.getElementById("assistantContextTitle").textContent = state.profile?.fieldName || "No field selected";
  document.getElementById("assistantContextLocation").textContent = context.location;
  document.getElementById("assistantContextCrop").textContent = context.crop;
  document.getElementById("assistantContextSoil").textContent = context.soil;
  document.getElementById("assistantContextWater").textContent = context.water;
}

// ---- Irrigation dates, calendar files, field map pictures and the printable report ----

const fmtDay = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
const todayIso = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in the farmer's own time zone

function irrigationLine(x) {
  const mm = x.gross_mm ? ` · about ${x.gross_mm} mm` : "";
  const expected = x.rounds?.[0] ? ` Next round is expected around ${fmtDay(x.rounds[0].date)}.` : "";
  if (x.status === "now") return `Irrigate today${mm}`;
  if (x.status === "soon") return `Irrigate ${fmtDay(x.due)} (${x.in_days === 1 ? "tomorrow" : `in ${x.in_days} days`})${mm}`;
  if (x.status === "wait_rain") return `Hold: about ${x.rain_mm} mm of rain is due in 3 days. Check the field afterwards.`;
  if (x.status === "not_needed") return `No irrigation needed in the next 14 days.${expected}`;
  if (x.status === "outlook") return `Season outlook: about ${x.gross_mm} mm over ${x.irrigations} rounds${x.rounds?.[0] ? `, first around ${fmtDay(x.rounds[0].date)}` : ""}`;
  if (x.status === "before_sowing") return `Sowing in ${x.days_to_sowing} day${x.days_to_sowing === 1 ? "" : "s"}`;
  return "Season finished for this planting date";
}

// Every dated irrigation for the chosen crops: the next one from the forecast plus the typical rounds later in the season.
function irrigationEvents(items) {
  const events = [];
  const add = (x, date, mm, label) => { if (date >= todayIso() && !events.some((e) => e.crop === x.crop && e.date === date)) events.push({ crop: x.crop, date, mm, label }); };
  (items || []).forEach((x) => {
    if (x.status === "now") add(x, todayIso(), x.gross_mm, "Irrigate now");
    if (x.status === "soon") add(x, x.due, x.gross_mm, "Irrigate");
    (x.rounds || []).forEach((r) => add(x, r.date, r.gross_mm, "Expected irrigation"));
  });
  return events.sort((a, b) => a.date.localeCompare(b.date));
}

const compactDate = (iso) => iso.replaceAll("-", "");
const nextDay = (iso) => new Date(Date.parse(`${iso}T00:00:00Z`) + 86400000).toISOString().slice(0, 10);

function eventText(ev, fieldName) {
  return { title: `Irrigate ${ev.crop} · ${fieldName}`, details: `${ev.label}${ev.mm ? `: about ${ev.mm} mm` : ""} for ${ev.crop} in ${fieldName}. Dates come from the forecast and typical weather, so check the soil first. Planned with Dhartisense.` };
}

function googleCalendarLink(ev, fieldName) {
  const t = eventText(ev, fieldName);
  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(t.title)}&details=${encodeURIComponent(t.details)}&dates=${compactDate(ev.date)}/${compactDate(nextDay(ev.date))}`;
}

// An .ics file opens in Google Calendar, Apple Calendar and Outlook. Each event reminds at 9 pm the evening before and 6 am that day.
function downloadCalendar(events, fieldName) {
  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Dhartisense//Irrigation//EN", "CALSCALE:GREGORIAN"];
  events.forEach((ev, i) => {
    const t = eventText(ev, fieldName);
    lines.push("BEGIN:VEVENT", `UID:${Date.now()}-${i}-${compactDate(ev.date)}@dhartisense`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${compactDate(ev.date)}`, `DTEND;VALUE=DATE:${compactDate(nextDay(ev.date))}`, `SUMMARY:${t.title}`, `DESCRIPTION:${t.details}`,
      "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Irrigation tomorrow", "TRIGGER:-PT3H", "END:VALARM", "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Irrigation today", "TRIGGER:PT6H", "END:VALARM", "END:VEVENT");
  });
  lines.push("END:VCALENDAR");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([lines.join("\r\n")], { type: "text/calendar" }));
  link.download = `irrigation-${fieldName.replace(/[^\w-]+/g, "-").toLowerCase()}.ics`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 4000);
}

const TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

// A still satellite picture of the saved boundary (overview and report).
function drawFieldMap(key, containerId, p) {
  const box = document.getElementById(containerId);
  if (!box || !window.L) return false;
  const has = p?.polygon?.length >= 3;
  box.hidden = !has;
  if (!has) { state[key]?.remove(); state[key] = null; return false; }
  if (!box.offsetWidth) return has; // the page is not showing yet; setView draws it when it is
  if (state[key] && state[key].getContainer() !== box) { state[key].remove(); state[key] = null; }
  if (!state[key]) {
    state[key] = L.map(box, { zoomControl: false, dragging: false, scrollWheelZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false });
    L.tileLayer(TILES, { maxZoom: 19, maxNativeZoom: 18, attribution: "Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community" }).addTo(state[key]);
  }
  const m = state[key];
  if (m._fieldShape) m.removeLayer(m._fieldShape);
  m._fieldShape = L.polygon(p.polygon, { color: "#ffe066", weight: 3, fillColor: "#87aa69", fillOpacity: 0.25 }).addTo(m);
  m.invalidateSize();
  m.fitBounds(p.polygon, { maxZoom: 18, padding: [18, 18] });
  return true;
}

function renderMiniMaps() {
  const p = state.profile;
  const shown = drawFieldMap("summaryMapObj", "summaryMap", p);
  document.getElementById("summaryMapPlaceholder").hidden = Boolean(p?.polygon?.length >= 3);
  if (!shown && p?.polygon?.length >= 3) setTimeout(renderMiniMaps, 120);
  drawFieldMap("reportMapObj", "reportMap", p);
}

function renderReport() {
  const p = state.profile;
  const when = new Date().toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  document.getElementById("reportTitle").textContent = p ? `${fieldTitle(p)} field report` : "Your farm report will appear here";
  document.getElementById("reportSubtitle").textContent = p ? `${p.farmName ? `${p.farmName} · ` : ""}${state.user?.name || "Farmer"} · prepared ${when}` : "Add a field and its details to create a report.";
  document.getElementById("reportArea").textContent = `Area ${formatArea(p?.areaHa)}`;
  document.getElementById("reportCrop").textContent = (p?.growing?.length ? `Growing ${growingNames(p).join(", ")}` : `Best crop ${p?.cropPlan?.top?.[0]?.crop || p?.crop || "not planned yet"}`);
  document.getElementById("reportDate").textContent = p?.updatedAt ? `Field updated ${new Date(p.updatedAt).toLocaleDateString()}` : "";
  const body = document.getElementById("reportBody");
  if (!p) { body.innerHTML = '<div class="report-section"><p class="muted-text">No field yet. Add a field on the Overview page and your report fills in as you use Crop plan and Water &amp; nutrients.</p></div>'; return; }
  const row = (k, v) => (v ? `<div><span>${k}</span><b>${escapeHtml(v)}</b></div>` : "");
  const section = (title, inner) => `<section class="report-section"><h3>${title}</h3>${inner}</section>`;
  const empty = (text) => `<p class="muted-text">${text}</p>`;
  const table = (head, rows) => `<div class="table-scroll"><table class="report-table"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${escapeHtml(c ?? "—")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  const dims = p.lengthM ? `${fmtLength(p.lengthM)} × ${fmtLength(p.widthM)}` : "";
  const profile = section("Field profile", `<div class="report-facts">${row("Location", p.location?.name)}${row("Area", p.areaHa ? fmtAreaBoth(p.areaHa) : "")}${row("Perimeter", p.perimeterM ? fmtLength(p.perimeterM) : "")}${row("Length × width", dims)}${row("Direction", p.bearing != null ? fmtDirection(p.bearing) : "")}${row("Soil texture", p.texture)}${row("Soil pH", p.ph)}${row("Water source", p.waterSource)}${row("Irrigation method", p.irrigation)}${row("Growing", growingNames(p).join(", "))}${row("Current crop", p.crop)}${row("Growth stage", p.stage)}</div>`);
  const map = section("Field boundary", p.polygon?.length >= 3 ? '<div id="reportMap" class="report-map"></div>' : empty("The boundary has not been drawn yet. Open My fields and mark the corners."));
  const cur = state.weather?.data?.current;
  const daily = state.weather?.data?.daily;
  const weather = section("Weather", cur ? `<p><b>${tempText(cur.temperature_2m)}</b> now · ${weatherCodeLabel(cur.weather_code)}${daily?.time?.length ? ` · next days: ${daily.time.slice(0, 3).map((d, i) => `${new Date(d).toLocaleDateString(undefined, { weekday: "short" })} ${tempText(daily.temperature_2m_max[i])} (${Math.round(daily.precipitation_probability_max[i] || 0)}% rain)`).join(", ")}` : ""}.</p><p class="muted-text">Source: Open-Meteo forecast for the field location.</p>` : empty("Weather loads when the field has a location."));
  const cp = p.cropPlan;
  const crops = section("Recommended crops", cp?.top?.length ? table(["#", "Crop", "Fit score", "Match", "Typical local yield", "Irrigation need"], cp.top.map((o, i) => [i + 1, o.crop, o.score, o.label || "", o.yield ? `${o.yield} t/ha` : "—", o.irrigation_mm ? `about ${o.irrigation_mm} mm` : "—"])) + empty(`Ranked for planting on ${cp.date}. Scores combine what farmers nearby grow, weather history, soil and irrigation; they are not a yield guarantee.`) : empty("Run Crop plan to see the five best crops for this field."));
  const wp = p.waterPlan;
  const events = irrigationEvents(wp?.items);
  const water = section("Irrigation schedule", wp?.items?.length ? table(["Crop", "Advice"], wp.items.map((x) => [x.crop, irrigationLine(x)])) + (events.length ? `<h4>Next dated irrigations${events.length > 10 ? " (first 10; the Water page has the rest)" : ""}</h4>${table(["Date", "Crop", "Amount"], events.slice(0, 10).map((e) => [fmtDay(e.date), e.crop, e.mm ? `about ${e.mm} mm` : "—"]))}` : "") + empty(`Made on ${new Date(wp.at).toLocaleDateString()} from the water balance and weather forecast. Re-run on the Water page for fresh advice.`) : empty("Make a schedule on the Water &amp; nutrients page."));
  const np = p.nutrientPlan;
  const fert = section("Fertiliser plan", np?.items?.length ? table(["Crop", "N : P₂O₅ : K₂O (kg/ha)", "Urea", "DAP", "MOP", "For your field"], np.items.map((x) => [x.crop, `${x.dose.N} : ${x.dose.P} : ${x.dose.K}`, `${x.products_kg_ha.Urea} kg/ha`, `${x.products_kg_ha.DAP} kg/ha`, `${x.products_kg_ha.MOP} kg/ha`, x.field_kg ? `urea ${x.field_kg.Urea}, DAP ${x.field_kg.DAP}, MOP ${x.field_kg.MOP} kg` : "—"])) + empty(`Based on the soil-test values you entered (${p.nutrients?.N || "–"} N, ${p.nutrients?.P || "–"} P, ${p.nutrients?.K || "–"} K kg/ha). General doses are indicative; follow your Soil Health Card or local advice.`) : empty("Enter a soil test on the Water &amp; nutrients page to get a fertiliser plan."));
  const nd = p.ndvi;
  const sat = section("Crop health (satellite)", nd ? `<div class="report-facts">${row("Greenness (NDVI)", `${nd.mean.toFixed(2)} on ${nd.date}`)}${row("Reading", nd.label)}${row("Change", nd.delta == null ? "" : `${nd.delta > 0 ? "+" : ""}${nd.delta.toFixed(2)} (${nd.trend})`)}</div>${empty("Sentinel-2 satellite, 10 m pixels. NDVI shows how green the field looks; it does not diagnose a cause.")}` : empty("Open Crop health to read your field from satellite images."));
  const ob = p.waterObservation;
  const obs = section("Your latest observations", ob && (ob.soil || ob.lastIrrigation || ob.recentRain || ob.notes) ? `<div class="report-facts">${row("Soil surface", ob.soil)}${row("Last irrigation", ob.lastIrrigation)}${row("Recent rain", ob.recentRain)}${row("Notes", ob.notes)}</div>` : empty("No observations saved yet."));
  const checks = readChecks().slice(0, 5);
  const health = section("Plant health checks (this device)", checks.length ? table(["Date", "Crop", "Finding"], checks.map((c) => [new Date(c.id).toLocaleDateString(), c.crop, c.condition])) + empty("A photo check is a likely classification, not a confirmed diagnosis.") : empty("No plant checks yet."));
  body.innerHTML = profile + map + weather + sat + crops + water + fert + obs + health + `<p class="report-foot">Dhartisense report · advice is guidance based on public data and the details you entered. Check prices, local conditions and expert advice before you act.</p>`;
  renderMiniMaps();
}


function openModal() {
  const modal = document.getElementById("setupModal");
  modal.hidden = false;
  document.getElementById("quickFarmName").value = state.profile?.farmName || state.fields[0]?.farmName || "";
  document.getElementById("quickFieldName").value = state.profile?.fieldName || "";
  document.getElementById("quickLocation").value = state.profile?.location?.name || "";
  document.getElementById("quickLocation").focus();
}

function closeModal() {
  document.getElementById("setupModal").hidden = true;
}

async function searchLocation() {
  const input = document.getElementById("quickLocation");
  const query = input.value.trim();
  const results = document.getElementById("locationResults");
  if (query.length < 2) return;
  results.innerHTML = '<span class="muted-text">Searching locations…</span>';
  try {
    const places = await searchPlaces(query);
    if (!places.length) {
      results.innerHTML = '<span class="muted-text">No place found. Try a nearby town, or paste coordinates like 18.52, 73.85.</span>';
      return;
    }
    results.innerHTML = "";
    places.forEach((place) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "location-result";
      button.textContent = place.name;
      button.addEventListener("click", () => {
        state.selectedLocation = { name: place.name, lat: place.lat, lon: place.lon };
        input.value = place.name;
        results.innerHTML = '<span class="status-pill green">Location selected</span>';
      });
      results.appendChild(button);
    });
  } catch {
    results.innerHTML = '<span class="muted-text">Location search is unavailable. Check your connection and try again.</span>';
  }
}

const pickShape = (m) => ({ areaHa: m.areaHa, perimeterM: m.perimeterM, lengthM: m.lengthM, widthM: m.widthM, bearing: m.bearing });

function saveFieldFromForm(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const existing = state.profile || {};
  const location = state.selectedLocation || existing.location;
  if (!location) {
    setFeedback("fieldFeedback", "Choose a location in the setup window or use your device location first.", true);
    return;
  }
  state.profile = Object.assign(existing, {
    farmName: String(formData.get("farmName") || "").trim(),
    fieldName: String(formData.get("fieldName") || "").trim(),
    crop: String(formData.get("crop") || "") || existing.growing?.[0]?.crop || "",
    stage: String(formData.get("stage") || ""),
    texture: String(formData.get("texture") || ""),
    ph: String(formData.get("ph") || "").trim(),
    waterSource: String(formData.get("waterSource") || ""),
    irrigation: String(formData.get("irrigation") || ""),
    soilTestKnown: document.getElementById("soilTestKnown").checked,
    location,
  });
  if (state.mapClosed && state.mapPoints.length >= 3) Object.assign(state.profile, { polygon: state.mapPoints.map((p) => [p[0], p[1]]), ...pickShape(polygonMetrics(state.mapPoints)) });
  saveProfile();
  if (state.profile.location) fetchWeather();
  flashButton(event.submitter || event.target.querySelector('button[type="submit"]'), "Saved ✓");
  toast(`Field “${fieldTitle(state.profile)}” saved to your account.`);
}

function handleQuickSetup(event) {
  event.preventDefault();
  const farmName = document.getElementById("quickFarmName").value.trim();
  const fieldName = document.getElementById("quickFieldName").value.trim();
  if (!state.selectedLocation && !state.profile?.location) {
    document.getElementById("locationResults").innerHTML = '<span class="form-feedback error">Search and select a location first.</span>';
    return;
  }
  state.profile = Object.assign(state.profile || {}, { farmName, fieldName, location: state.selectedLocation || state.profile?.location, areaHa: state.profile?.areaHa || 0, polygon: state.profile?.polygon || null });
  saveProfile();
  closeModal();
  setView("fields");
  fetchWeather();
  setTimeout(() => { initMap(); showFieldOnMap(); state.map?.invalidateSize(); }, 150); // the map opens on the place you just chose, so you do not search again
  toast(`Field “${fieldName || "Unnamed field"}” created. Now trace its boundary on the map.`);
}

function useCurrentLocation() {
  if (!navigator.geolocation) {
    setFeedback("fieldFeedback", "Location access is not available in this browser.", true);
    return;
  }
  navigator.geolocation.getCurrentPosition((position) => {
    state.selectedLocation = { name: "Current device location", lat: position.coords.latitude, lon: position.coords.longitude };
    state.profile = Object.assign(state.profile || {}, { location: state.selectedLocation });
    if (state.map) state.map.setView([state.selectedLocation.lat, state.selectedLocation.lon], 16);
    saveProfile();
    fetchWeather();
    setFeedback("fieldFeedback", "Device location added. Draw your field boundary on the map.");
  }, () => setFeedback("fieldFeedback", "Location permission was not granted. Search for a nearby place instead.", true));
}

const IRRIGATED_METHODS = ["Flood", "Furrow", "Sprinkler", "Drip"];
const IRRIGATED_SOURCES = ["Open well", "Borewell", "Canal", "Stored water"];

function isIrrigated(p) {
  return IRRIGATED_METHODS.includes(p?.irrigation) || IRRIGATED_SOURCES.includes(p?.waterSource);
}

function fieldTitle(p) {
  return /[\p{L}\p{N}]/u.test(p?.fieldName || "") ? p.fieldName : "Unnamed field";  // a name like ",," has nothing to show
}

function renderCropPlanInputs() {
  const p = state.profile;
  const select = document.getElementById("planField");
  if (!select) return;
  const label = (f) => `${escapeHtml(fieldTitle(f))}${f.areaHa ? ` · ${formatArea(f.areaHa)}` : ""}`;
  select.innerHTML = state.fields.length ? state.fields.map((f) => `<option value="${f.id}"${p?.id === f.id ? " selected" : ""}>${label(f)}</option>`).join("") : p ? `<option>${label(p)}</option>` : "<option>No field saved</option>";
  document.getElementById("planSoil").textContent = p
    ? `Soil pH ${p.ph || "not entered"} · texture ${p.texture ? p.texture.toLowerCase() : "not entered"} · ${isIrrigated(p) ? "irrigated" : "no irrigation entered (rain-fed)"} · edit these in My fields.`
    : "Save a field in My fields first.";
  const date = document.getElementById("plantingDate");
  if (!date.value) date.value = new Date().toISOString().slice(0, 10);
  renderGrowingBar();
}

function fillCropChips(names) {
  const box = document.getElementById("cropChoices");
  box.innerHTML = names.map((n) => `<button type="button" class="choice-chip" data-crop="${escapeHtml(n)}">${escapeHtml(n)}</button>`).join("");
  box.addEventListener("click", (event) => event.target.closest(".choice-chip")?.classList.toggle("selected"));
}

const growingNames = (p = state.profile) => (p?.growing || []).map((g) => g.crop);

function growButton(crop) {
  const on = growingNames().includes(crop);
  return `<button type="button" class="button ${on ? "primary" : "secondary"} grow-btn" data-grow-crop="${escapeHtml(crop)}">${on ? "✓ Growing this" : "＋ I will grow this"}</button>`;
}

function renderGrowingBar() {
  const bar = document.getElementById("growingBar");
  if (!bar) return;
  const list = state.profile?.growing || [];
  bar.hidden = !list.length;
  bar.innerHTML = list.length ? `<span class="growing-label">Growing on ${escapeHtml(fieldTitle(state.profile))}:</span>${list.map((g) => `<span class="growing-chip">${escapeHtml(g.crop)}<button type="button" data-grow-remove="${escapeHtml(g.crop)}" aria-label="Stop growing ${escapeHtml(g.crop)}">×</button></span>`).join("")}` : "";
}

function toggleGrowing(crop) {
  const p = state.profile;
  if (!p) return toast("Save a field first.", "error");
  p.growing = p.growing || [];
  const at = p.growing.findIndex((g) => g.crop === crop);
  if (at >= 0) {
    p.growing.splice(at, 1);
    toast(`${crop} removed from what you grow on ${fieldTitle(p)}.`, "info");
  } else {
    p.growing.push({ crop, planting: document.getElementById("plantingDate").value || todayIso(), added: new Date().toISOString() });
    toast(`${crop} added to what you grow on ${fieldTitle(p)}. It now shows on your Overview.`);
  }
  if (p.growing.length) p.crop = p.growing[0].crop;
  saveProfile();
  document.querySelectorAll("[data-grow-crop]").forEach((b) => {
    const on = growingNames().includes(b.dataset.growCrop);
    b.classList.toggle("primary", on);
    b.classList.toggle("secondary", !on);
    b.textContent = on ? "✓ Growing this" : "＋ I will grow this";
  });
}

function cropCard(o, mine) {
  const f = o.factors;
  const bar = (label, v) => (v == null ? "" : `<span class="fit-chip fit-${v >= 0.75 ? "good" : v >= 0.4 ? "fair" : "poor"}">${label} ${Math.round(v * 100)}%</span>`);
  const tags = [`${o.cycle_days}-day season`, o.irrigation_mm ? `needs about ${o.irrigation_mm} mm irrigation` : "", o.regional ? `grown on ${Math.round(o.regional.share * 100)}% of farmland nearby${o.regional.yield ? ` · typical yield ${o.regional.yield} t/ha` : ""}` : ""].filter(Boolean);
  return `<li class="crop-card${mine ? " mine" : ""}"><div class="crop-rank-no">${o.rank}</div><div class="crop-body"><div class="crop-head"><strong>${escapeHtml(o.crop)}</strong><span class="status-pill ${o.score >= 75 ? "green" : o.score >= 55 ? "amber" : "neutral"}">${o.label} · ${o.score}</span></div>
    <div class="fit-chips">${bar("Temperature", f.temperature)}${bar("Rainfall", f.rainfall)}${bar("Soil pH", f.ph)}${bar("Soil type", f.soil)}</div>
    <ul class="crop-reasons">${o.reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
    <div class="crop-tags">${tags.map((t) => `<span>${escapeHtml(t)}</span>`).join("")}</div>${o.sowing_note ? `<p class="sowing-note">${escapeHtml(o.sowing_note)}</p>` : ""}${growButton(o.crop)}${o.score > 0 ? `<button class="button secondary plan-btn" type="button" data-plan-crop="${escapeHtml(o.crop)}"><i data-lucide="layout-grid"></i> Plan this field</button>` : ""}</div></li>`;
}

async function handleCropPlan(event) {
  event.preventDefault();
  const result = document.getElementById("cropResult");
  const message = (icon, title, text) => { result.innerHTML = `<div class="empty-result"><div class="empty-icon"><i data-lucide="${icon}"></i></div><span class="eyebrow">Crop suitability</span><h2>${title}</h2><p>${text}</p></div>`; iconRefresh(); };
  const p = state.profile;
  if (!p?.location) return message("map", "Map a field first", "Save a field with its location in My fields, then come back.");
  message("loader-circle", "Checking five years of weather", "Matching every crop's needs against your location and planting date. This takes a few seconds.");
  const picks = [...document.querySelectorAll("#cropChoices .choice-chip.selected")].map((chip) => chip.dataset.crop);
  try {
    const response = await fetch("/api/crop-rank", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lat: p.location.lat, lon: p.location.lon, planting_date: document.getElementById("plantingDate").value, objective: document.getElementById("farmObjective").value, ph: p.ph, texture: p.texture, irrigated: isIrrigated(p), irrigation: p.irrigation, candidate_crops: picks }) });
    const r = await response.json();
    if (!r.ready) return message("clipboard-list", "Could not rank crops", escapeHtml(r.error || "Try again in a moment."));
    state.lastRank = r;
    renderWaterCrops();
    toast(`Top ${r.options.length} crops ready. Tap "I will grow this" on the ones you choose.`);
    p.cropPlan = { at: new Date().toISOString(), date: r.planting_date, top: r.options.map((o) => ({ crop: o.crop, score: o.score, label: o.label, yield: o.regional?.yield || null, irrigation_mm: o.irrigation_mm || 0 })) };
    saveProfile();
    if (!r.options.length) return message("droplets", "No crop fits this date", isIrrigated(p) ? "Even with irrigation, the temperature at this location and date is outside every crop's range. Try another planting date." : "With no irrigation, the rain expected over the season is too low or too high for every crop. Add your water source and irrigation method in My fields, or try another planting date.");
    const name = fieldTitle(p);
    const few = r.options.length < 5 ? `<p class="source-note"><i data-lucide="info"></i><span>Only ${r.options.length} crop${r.options.length > 1 ? "s" : ""} fit${r.options.length > 1 ? "" : "s"} this field and date well enough to recommend.${isIrrigated(p) ? "" : " Adding irrigation in My fields would open up more."}</span></p>` : "";
    const date = new Date(r.planting_date).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
    result.innerHTML = `<div class="model-result"><div class="model-result-heading"><div><span class="eyebrow">Best crops for ${escapeHtml(name)}</span><h2>${r.options.length < 5 ? `Best ${r.options.length} to plant` : "Top 5 to plant"} on ${escapeHtml(date)}</h2></div></div>
      <div id="cropPager"></div>${few}
      <p class="source-note"><i data-lucide="info"></i><span>${r.regional_districts.length ? `Ranked first by what farmers near you grow in this season (government district statistics 2008–2015: ${escapeHtml(r.regional_districts.join("; "))}), then adjusted by how well each crop's needs (${escapeHtml(r.source)}) match ${escapeHtml(r.history)}, your soil and your irrigation.` : `No district farming data covers this location, so crops are ranked only by how well their needs (${escapeHtml(r.source)}) match ${escapeHtml(r.history)}, your soil and your irrigation.`}${r.week ? ` This week's forecast averages ${Math.round(r.week.temp)} °C.` : ""} Scores show suitability and local practice, not a yield guarantee. Check prices and local advice before you commit.</span></p></div>`;
    makePager(document.getElementById("cropPager"), [
      ...r.options.map((o) => ({ title: `${o.rank}. ${escapeHtml(o.crop)}`, html: `<ol class="crop-rank">${cropCard(o, false)}</ol>` })),
      ...r.picks.map((o) => ({ title: `${escapeHtml(o.crop)} · you asked about it`, html: `<ol class="crop-rank">${cropCard(o, true)}</ol>` })),
    ], "crop");
    iconRefresh();
  } catch {
    message("wifi-off", "Crop service is offline", "Your field profile is saved. Start the server and try again.");
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
}

function handleWaterForm(event) {
  event.preventDefault();
  if (!state.profile) {
    setFeedback("waterFeedback", "Save a field profile first.", true);
    return;
  }
  const nutrientInputs = [...document.querySelectorAll(".nutrient-inputs input")].map((input) => input.value.trim());
  state.profile.nutrients = { N: nutrientInputs[0] || "", P: nutrientInputs[1] || "", K: nutrientInputs[2] || "" };
  state.profile.waterObservation = { soil: document.getElementById("soilObservation").value, lastIrrigation: document.getElementById("lastIrrigation").value, recentRain: document.getElementById("recentRain").value, notes: document.getElementById("waterNotes").value.trim(), recordedAt: new Date().toISOString() };
  saveProfile();
  toast("Observation saved to your account.");
  runWaterPlan();
}

const waterSel = new Set();

function renderWaterCrops() {
  const box = document.getElementById("waterCrops");
  if (!box) return;
  const suggested = (state.lastRank?.options || []).map((o) => o.crop);
  const names = [...suggested, ...[...waterSel].filter((n) => !suggested.includes(n))];
  box.innerHTML = names.map((n) => `<button type="button" class="choice-chip${waterSel.has(n) ? " selected" : ""}" data-crop="${escapeHtml(n)}">${suggested.includes(n) ? `${suggested.indexOf(n) + 1} · ` : ""}${escapeHtml(n)}</button>`).join("");
  document.getElementById("waterCropHint").textContent = suggested.length ? "· suggested crops are numbered by rank; tap to choose one or more" : state.lastRank === undefined && state.profile?.location ? "· finding your suggested crops…" : "· add crops below";
  document.getElementById("nutrientPlanBtn").addEventListener("click", runNutrientPlan);
  document.getElementById("waterAllCrops").disabled = !suggested.length;
}

async function openWater() {
  const date = document.getElementById("waterPlantingDate");
  if (!date.value) date.value = document.getElementById("plantingDate").value || new Date().toISOString().slice(0, 10);
  const p = state.profile;
  if (!waterSel.size) growingNames(p).forEach((name) => waterSel.add(name)); // the crops you chose to grow are ready to plan
  if (state.lastRank || !p?.location || state.rankingBusy) return renderWaterCrops();
  state.rankingBusy = true;
  renderWaterCrops();
  try {  // same ranking as the Crop plan page, so the suggestions match
    const r = await (await fetch("/api/crop-rank", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lat: p.location.lat, lon: p.location.lon, planting_date: date.value, objective: "fit", ph: p.ph, texture: p.texture, irrigated: isIrrigated(p), candidate_crops: [] }) })).json();
    if (r.ready) state.lastRank = r;
  } catch { /* the farmer can still add crops by hand */ }
  state.rankingBusy = false;
  if (!state.lastRank) state.lastRank = { options: [] };
  renderWaterCrops();
}

async function runNutrientPlan() {
  const box = document.getElementById("nutrientResult");
  const p = state.profile;
  const say = (text) => { box.innerHTML = `<p class="source-note"><i data-lucide="info"></i><span>${text}</span></p>`; iconRefresh(); };
  if (!p) return say("Save a field profile first.");
  if (!waterSel.size) return say("Choose one or more crops in the irrigation panel above first.");
  const [N, P, K] = [...document.querySelectorAll(".nutrient-inputs input")].map((input) => input.value.trim());
  p.nutrients = { N, P, K };
  saveProfile();
  say("Working out the fertiliser plan…");
  try {
    const r = await (await fetch("/api/nutrient-plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ planting_date: document.getElementById("waterPlantingDate").value, area_ha: p.areaHa, crops: [...waterSel], N, P, K }) })).json();
    if (!r.ready) return say(escapeHtml(r.error || "Could not make the plan."));
    p.nutrientPlan = { at: new Date().toISOString(), items: r.plans.map((x) => ({ crop: x.crop, dose: x.dose, products_kg_ha: x.products_kg_ha, field_kg: x.field_kg, ratings: x.ratings })) };
    saveProfile();
    box.innerHTML = `<div id="nutrientPager"></div><p class="source-note"><i data-lucide="info"></i><span>${escapeHtml(r.source)}. Check your state's recommendation or Soil Health Card before buying fertiliser.</span></p>`;
    makePager(document.getElementById("nutrientPager"), r.plans.map((x) => ({ title: escapeHtml(x.crop), html: nutrientCard(x) })), "crop");
    iconRefresh();
    toast(`Fertiliser plan ready for ${r.plans.length} crop${r.plans.length > 1 ? "s" : ""}.`);
  } catch {
    say("The service is offline. Start the server and try again.");
  }
}

function nutrientCard(x) {
  const tone = { low: "red", medium: "green", high: "amber", unknown: "neutral" };
  const chips = ["N", "P", "K"].map((k) => `<span class="status-pill ${tone[x.ratings[k]]}">${{ N: "Nitrogen", P: "Phosphorus", K: "Potassium" }[k]}: ${x.ratings[k] === "unknown" ? "no test" : x.ratings[k]}</span>`).join(" ");
  const date = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "");
  const f = x.products_kg_ha;
  const field = x.field_kg;
  const bags = (kg) => `${Math.round(kg).toLocaleString()} kg`;
  return `<div class="water-card"><div class="crop-head"><strong>${escapeHtml(x.crop)}</strong></div><div class="fit-chips">${chips}</div>
    <p>Nutrients to apply: <b>${x.dose.N}</b> N · <b>${x.dose.P}</b> P₂O₅ · <b>${x.dose.K}</b> K₂O kg/ha (general dose ${x.general.N}:${x.general.P}:${x.general.K}, adjusted by your soil test).</p>
    <p>As fertiliser per hectare: urea ${f.Urea} kg · DAP ${f.DAP} kg · MOP ${f.MOP} kg${field ? `. For your field: urea ${bags(field.Urea)}, DAP ${bags(field.DAP)}, MOP ${bags(field.MOP)}.` : "."}</p>
    <p class="water-small">Nitrogen timing: ${x.applications.map((a) => `${Math.round(a.share * 100)}% ${a.label.toLowerCase()}${a.date ? ` (${date(a.date)})` : ""}`).join(", then ")}. Apply all phosphorus and potassium at ${x.legume ? "sowing" : "sowing or planting"}.${x.legume ? " Legumes fix much of their own nitrogen, so nitrogen is a small starter dose." : ""}</p>
    <p class="water-small">${x.checked ? "General dose matches a published guide read for this project." : "General dose is a typical national figure, not looked up for your state."}</p></div>`;
}

async function runWaterPlan() {
  const box = document.getElementById("waterResult");
  const p = state.profile;
  const say = (title, text) => { box.innerHTML = `<div class="empty-result"><div class="empty-icon"><i data-lucide="droplets"></i></div><span class="eyebrow">Irrigation schedule</span><h2>${title}</h2><p>${text}</p></div>`; iconRefresh(); };
  if (!p?.location) return say("Map a field first", "Save a field with its location in My fields.");
  if (!waterSel.size) return say("Choose a crop", "Tap one or more crops on the left, then make the schedule.");
  say("Working out the schedule", "Reading evapotranspiration and rain for your location.");
  try {
    const r = await (await fetch("/api/water-plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lat: p.location.lat, lon: p.location.lon, planting_date: document.getElementById("waterPlantingDate").value, crops: [...waterSel], texture: p.texture, irrigation: p.irrigation, last_irrigation: document.getElementById("lastIrrigation").value, observation: document.getElementById("soilObservation").value }) })).json();
    if (!r.ready) return say("Could not make the schedule", escapeHtml(r.error || "Try again in a moment."));
    box.innerHTML = `<div class="panel-heading"><div><span class="eyebrow">Irrigation schedule</span><h2>${r.plans.length > 1 ? "Water plan for each crop" : "Water plan"}</h2></div></div><div id="waterPager"></div>${irrigationEvents(r.plans).length ? `<button class="button secondary full-width" type="button" id="downloadCalendar"><i data-lucide="calendar-days"></i> Download all dates with reminders (.ics)</button>` : ""}
      <p class="source-note"><i data-lucide="info"></i><span>${escapeHtml(r.source)}. Soil water holding is typical for ${escapeHtml(p.texture ? p.texture.toLowerCase() : "an average")} soil, not measured. Treat dates as a prompt to check the field, not an order.</span></p>`;
    makePager(document.getElementById("waterPager"), r.plans.map((x) => ({ title: escapeHtml(x.crop), html: waterCard(x, p) })), "crop");
    iconRefresh();
    toast(`Irrigation schedule ready for ${r.plans.length} crop${r.plans.length > 1 ? "s" : ""}.`);
    document.getElementById("downloadCalendar")?.addEventListener("click", () => downloadCalendar(irrigationEvents(r.plans), fieldTitle(p)));
    p.waterPlan = { at: new Date().toISOString(), planting: r.planting_date, items: r.plans.map(({ days, ...rest }) => rest) };
    saveProfile();
  } catch {
    say("Crop service is offline", "Start the server and try again.");
  }
}

function waterCard(x, p) {
  const area = p?.areaHa ? (mm) => ` (about ${Math.round(mm * 10 * p.areaHa).toLocaleString()} m³ for your ${formatArea(p.areaHa)})` : () => "";
  const date = (iso) => new Date(iso).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
  const tag = x.approximate ? `<span class="fit-chip fit-fair" title="${escapeHtml(x.basis)}">approximate data</span>` : "";
  let head, tone = "neutral", body = "";
  if (x.status === "no_history") head = "Not enough weather history";
  else if (x.status === "outlook") {
    head = `Season outlook: about ${x.gross_mm} mm of irrigation`;
    tone = "amber";
    body = `<p>Over ${x.season_days} days the crop uses about ${x.etc_mm} mm of water and typical rain gives ${x.rain_mm} mm, from the same dates in the last ${x.years} years. Expect around ${x.irrigations} irrigation rounds${area(x.gross_mm)}. A day-by-day schedule starts once you plant.</p>`;
  } else if (x.status === "before_sowing") head = `Sowing in ${x.days_to_sowing} day${x.days_to_sowing === 1 ? "" : "s"}`;
  else if (x.status === "season_over") head = "Season finished for this planting date";
  else {
    const w = Math.min(100, Math.round((x.depletion_mm / Math.max(1, x.raw_mm)) * 100));
    head = x.status === "now" ? `Irrigate today: about ${x.gross_mm} mm` : x.status === "soon" ? `Irrigate ${x.in_days === 1 ? "tomorrow" : `in ${x.in_days} days (${date(x.due)})`}: about ${x.gross_mm} mm` : "No irrigation needed in the next 14 days";
    if (x.status === "wait_rain") head = `Rain due: hold off irrigation (${x.rain_mm} mm in 3 days)`;
    tone = x.status === "now" ? "red" : x.status === "soon" || x.status === "wait_rain" ? "amber" : "green";
    body = `<div class="water-bar" title="Soil water used up before the crop is stressed"><span style="width:${w}%"></span></div><p class="water-small">${x.depletion_mm} of ${x.raw_mm} mm of easily available soil water used (${escapeHtml(x.basis_of_now)}).</p>
      <p>${escapeHtml(x.stage)}, day ${x.day_of_season} of ${x.season_days}. Over the next 7 days the crop uses about ${x.week.etc_mm} mm and the forecast gives ${x.week.rain_mm} mm of rain.</p>
      ${x.note ? `<p class="water-small">${escapeHtml(x.note)}</p>` : ""}${x.status === "wait_rain" ? `<p class="water-small">The soil is dry now, but forecast rain should cover most of the ${x.net_mm} mm it is missing. Check the field after the rain and irrigate only if it is still dry.</p>` : x.gross_mm ? `<p class="water-small">${x.net_mm} mm must reach the roots; at ${Math.round(x.efficiency * 100)}% application efficiency, apply ${x.gross_mm} mm${area(x.gross_mm)}.</p>` : ""}`;
  }
  const rounds = x.rounds?.length ? `<p class="water-small"><b>Dates:</b> ${x.rounds.map((rd) => `${fmtDay(rd.date)} (about ${rd.gross_mm} mm)`).join(" · ")}</p>` : "";
  const ev = irrigationEvents([x])[0];
  const cal = ev ? `<a class="text-button" target="_blank" rel="noopener" href="${googleCalendarLink(ev, fieldTitle(p))}"><i data-lucide="calendar-plus"></i> Add ${fmtDay(ev.date)} to Google Calendar</a>` : "";
  return `<div class="water-card"><div class="crop-head"><strong>${escapeHtml(x.crop)}</strong><span class="status-pill ${tone}">${head}</span></div>${tag}${body}${rounds}${cal}</div>`;
}

function handleImage(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) {
    setFeedback("imageFeedback", "Choose an image smaller than 8 MB.", true);
    return;
  }
  const reader = new FileReader();
  reader.onload = async () => {
    const result = document.querySelector('[data-view-panel="plant-health"] .result-panel');
    setFeedback("imageFeedback", `${file.name} is being checked…`);
    result.innerHTML = '<div class="empty-result"><div class="empty-icon"><i data-lucide="loader"></i></div><span class="eyebrow">Analysing</span><h2>Checking your photo…</h2></div>';
    iconRefresh();
    try {
      const response = await fetch("/api/disease-scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ image_base64: reader.result, crop: document.getElementById("plantCrop").value }) });
      const payload = await response.json();
      if (!payload.ready) {
        result.innerHTML = `<div class="empty-result"><div class="empty-icon"><i data-lucide="scan-line"></i></div><span class="eyebrow">Model status</span><h2>Could not check this image</h2><p>${escapeHtml(payload.reason || "The image could not be processed.")}</p></div>`;
        setFeedback("imageFeedback", `${file.name} could not be classified.`, true);
      } else {
        renderDiagnosis(result, payload, reader.result);
        setFeedback("imageFeedback", `${file.name} classified. Review the result before taking action.`);
      }
    } catch {
      result.innerHTML = '<div class="empty-result"><div class="empty-icon"><i data-lucide="scan-line"></i></div><span class="eyebrow">Model status</span><h2>Service unavailable</h2><p>The image service is unavailable. Your image was not saved.</p></div>';
      setFeedback("imageFeedback", "The image service is unavailable. Your image was not saved.", true);
    }
    iconRefresh();
  };
  reader.readAsDataURL(file);
}

let CHECKS_KEY = "dhartisense.plantChecks";

function readChecks() {
  try { return JSON.parse(localStorage.getItem(CHECKS_KEY)) || []; } catch { return []; }
}

function writeChecks(list) {
  try { localStorage.setItem(CHECKS_KEY, JSON.stringify(list.slice(0, 20))); } catch { /* storage unavailable: history is optional */ }
}

const openChecks = new Set();

function makeThumb(dataUrl, size = 140) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, size / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", 0.6));
    };
    img.onerror = () => resolve("");
    img.src = dataUrl;
  });
}

function clearPlantResult(quiet) {
  document.querySelector('[data-view-panel="plant-health"] .result-panel').innerHTML = initialPanels.plant;
  document.getElementById("plantImage").value = "";
  setFeedback("imageFeedback", "");
  state.lastDiagnosis = null;
  iconRefresh();
  if (quiet !== true) toast("Cleared. Ready for another photo.", "info");
}

function renderChecks() {
  const list = readChecks();
  document.getElementById("plantHistoryPanel").hidden = !list.length;
  document.getElementById("plantHistory").innerHTML = list.map((c) => {
    const pick = (value) => (c.feedback === value ? "selected" : "");
    const when = new Date(c.id).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    const confidence = c.confidence == null ? "Visual assessment" : `${Math.round(c.confidence * 100)}% confidence`;
    return `<div class="check-row" data-id="${c.id}"><div class="check-main">${c.thumb ? `<img class="check-thumb" src="${c.thumb}" alt="" />` : ""}<div><strong>${escapeHtml(c.crop)} · ${escapeHtml(c.condition)}</strong><span>${when} · ${c.source === "classifier" ? "Local model" : "Vision check"} · ${confidence}${c.field ? ` · ${escapeHtml(c.field)}` : ""}</span></div></div>
      <div class="check-actions"><button type="button" class="text-button" data-view>${openChecks.has(c.id) ? "Hide details" : "View details"}</button><button type="button" class="text-button danger" data-del>Delete</button></div>
      <div class="check-detail"${openChecks.has(c.id) ? "" : " hidden"}>${c.symptoms ? `<p><b>What was seen:</b> ${escapeHtml(c.symptoms)}</p>` : ""}<p><b>Advice:</b> ${escapeHtml(c.advice || "No advice was saved for this check.")}</p><div class="check-feedback" data-id="${c.id}"><span>Was this right?</span><button type="button" data-fb="yes" class="${pick("yes")}">Yes</button><button type="button" data-fb="no" class="${pick("no")}">No</button></div></div></div>`;
  }).join("");
}

function saveCheck(entry) {
  writeChecks([entry, ...readChecks()]);
  renderChecks();
}

function setCheckFeedback(event) {
  const row = event.target.closest(".check-row");
  if (!row) return;
  const id = Number(row.dataset.id);
  if (event.target.closest("[data-view]")) {
    if (openChecks.has(id)) openChecks.delete(id); else openChecks.add(id);
    return renderChecks();
  }
  if (event.target.closest("[data-del]")) {
    if (!window.confirm("Delete this plant check from your history?")) return;
    writeChecks(readChecks().filter((c) => c.id !== id));
    toast("Check deleted.", "info");
    return renderChecks();
  }
  const button = event.target.closest("[data-fb]");
  if (!button) return;
  writeChecks(readChecks().map((c) => (c.id === id ? { ...c, feedback: button.dataset.fb } : c)));
  renderChecks();
  toast("Thanks, your answer is saved.", "info");
}

// Cascade result -> one diagnosis. A confident local model wins; otherwise the vision check; otherwise the unsure local model.
function chooseDiagnosis(payload) {
  const top = payload.predictions[0];
  const vision = payload.vision && !payload.vision.error ? payload.vision : null;
  const fromModel = (source, confirmed) => ({ crop: top.crop, condition: top.healthy ? "Healthy" : top.condition, healthy: top.healthy, confidence: top.probability, source, confirmed });
  if (top && !payload.uncertain && !payload.no_disease_classes) return fromModel("classifier", true);
  if (vision) {
    const cause = vision.possible_causes[0];
    return { crop: vision.crop || document.getElementById("plantCrop").value || top?.crop || "plant", condition: vision.healthy ? "Healthy" : (cause?.name || "unidentified leaf problem"), healthy: vision.healthy, confidence: null, source: "vision", confirmed: false };
  }
  return fromModel("classifier", false);
}

async function fetchAdvice(diagnosis, vision, answers) {
  const response = await fetch("/api/disease-advice", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ crop: diagnosis.crop, condition: diagnosis.condition, confidence: diagnosis.confidence, symptoms: vision?.symptoms || "", answers, field: profileContext() }) });
  const advice = await response.json();
  return (advice.answer || "").replace(/[*#`]/g, "").trim();
}

async function renderDiagnosis(result, payload, imageUrl) {
  const d = chooseDiagnosis(payload);
  const vision = payload.vision && !payload.vision.error ? payload.vision : null;
  const pct = (p) => Math.round(p.probability * 100);
  const title = d.healthy ? `${d.crop} · looks healthy` : `${d.crop} · ${d.condition}${d.confirmed ? "" : " (possible)"}`;
  const pill = d.confirmed ? '<span class="status-pill green">Likely match</span>' : '<span class="status-pill amber">Needs confirmation</span>';
  const note = payload.no_disease_classes ? "The local model only knows healthy leaves for this crop, so a visual check was added."
    : payload.classifier && payload.uncertain ? "The local model was not sure, so a second visual check was added."
    : payload.classifier && !payload.crop_filtered ? "Choose your crop above and upload again for a more reliable result." : "";
  const visionNote = payload.vision?.error === "rate_limited" ? "The second visual check is busy right now (free-tier limit); showing the local model only."
    : payload.vision?.error ? "The second visual check is unavailable right now; showing the local model only." : "";
  const confidenceLine = d.confidence == null ? "Visual assessment · no confidence score" : `${Math.round(d.confidence * 100)}% model confidence`;
  const modelBlock = payload.predictions.length ? `<div class="model-options"><span class="eyebrow">Local model</span>${payload.predictions.map((p, i) => `<button type="button" class="model-option candidate" data-i="${i}"><div><strong>${escapeHtml(p.crop)} · ${escapeHtml(p.condition)}</strong></div><b>${pct(p)}%</b></button>`).join("")}${payload.uncertain ? '<span class="source-note">Not sure? Tap the one that matches your leaf to get advice for it.</span>' : ""}</div>` : "";
  const visionBlock = vision ? `<div class="vision-block"><span class="eyebrow">Visual check</span><p>${escapeHtml(vision.symptoms)}</p>${vision.possible_causes.map((c) => `<div class="model-option"><div><strong>${escapeHtml(c.name)}</strong><span>${escapeHtml(c.type)} · ${escapeHtml(c.why)}</span></div><b>${escapeHtml(c.likelihood)}</b></div>`).join("")}</div>` : "";
  const questions = vision?.follow_up_questions || [];
  const followBlock = questions.length ? `<div class="followups"><span class="eyebrow">Help narrow it down</span>${questions.map((q, i) => `<label class="followup"><span>${escapeHtml(q)}</span><input type="text" data-q="${i}" placeholder="Your answer" /></label>`).join("")}<button class="button secondary" id="refineAdvice" type="button">Update advice</button></div>` : "";
  result.innerHTML = `<div class="model-result"><div class="model-result-heading"><div><span class="eyebrow">Likely classification</span><h2>${escapeHtml(title)}</h2></div><div class="heading-actions">${pill}<button type="button" class="text-button" id="clearResult">Clear</button></div></div>
    <div class="diagnosis-top"><img class="diagnosis-photo" src="${imageUrl}" alt="Uploaded plant photo" /><div><strong>${confidenceLine}</strong>${note ? `<p>${escapeHtml(note)}</p>` : ""}${visionNote ? `<p>${escapeHtml(visionNote)}</p>` : ""}</div></div>
    ${modelBlock}${visionBlock}${followBlock}
    <div class="advice-box"><span class="eyebrow">Cure and prevention</span><p class="advice-text">Preparing advice…</p></div>
    <div class="result-actions"><button class="button secondary" id="learnMore" type="button" disabled><i data-lucide="message-circle"></i> Learn more</button><button class="button secondary" id="checkAnother" type="button"><i data-lucide="camera"></i> Check another plant</button></div>
    <p class="source-note"><i data-lucide="triangle-alert"></i><span>${escapeHtml(payload.warning)}</span></p></div>`;
  iconRefresh();
  result.querySelector("#clearResult").addEventListener("click", clearPlantResult);
  result.querySelector("#checkAnother").addEventListener("click", () => { clearPlantResult(true); document.getElementById("plantImage").click(); });
  state.lastDiagnosis = { crop: d.crop, condition: d.condition, confidence: d.confidence, symptoms: vision?.symptoms || "", advice: "" };
  const text = result.querySelector(".advice-text");
  const learn = result.querySelector("#learnMore");
  const load = async (answers) => {
    try {
      state.lastDiagnosis.advice = await fetchAdvice(d, vision, answers);
      text.textContent = state.lastDiagnosis.advice || "Advice is unavailable right now (check the Groq key and model). You can still ask in the assistant.";
    } catch {
      text.textContent = "Advice is unavailable right now. You can still ask in the assistant.";
    }
  };
  await load([]);
  saveCheck({ id: Date.now(), crop: d.crop, condition: d.condition, source: d.source, confidence: d.confidence, feedback: null, advice: state.lastDiagnosis.advice, symptoms: vision?.symptoms || "", field: state.profile ? fieldTitle(state.profile) : "", thumb: await makeThumb(imageUrl) });
  toast("Plant check saved to your history below.");
  learn.disabled = false;
  learn.addEventListener("click", openDiagnosisChat);
  result.querySelectorAll(".candidate").forEach((btn) => btn.addEventListener("click", async () => {
    const p = payload.predictions[Number(btn.dataset.i)];
    Object.assign(d, { crop: p.crop, condition: p.healthy ? "Healthy" : p.condition, healthy: p.healthy, confidence: p.probability });
    result.querySelector("h2").textContent = d.healthy ? `${d.crop} · looks healthy` : `${d.crop} · ${d.condition} (your pick)`;
    result.querySelectorAll(".candidate").forEach((b) => b.classList.toggle("selected", b === btn));
    Object.assign(state.lastDiagnosis, { crop: d.crop, condition: d.condition, confidence: d.confidence });
    text.textContent = "Updating advice…";
    await load([]);
  }));
  result.querySelector("#refineAdvice")?.addEventListener("click", async () => {
    const answers = [...result.querySelectorAll(".followup")].map((row, i) => ({ question: questions[i], answer: row.querySelector("input").value.trim() })).filter((a) => a.answer);
    if (!answers.length) return;
    text.textContent = "Updating advice…";
    await load(answers);
  });
}

function openDiagnosisChat() {
  const d = state.lastDiagnosis;
  if (!d) return;
  const sure = d.confidence == null ? "" : ` (${Math.round(d.confidence * 100)}% confidence)`;
  appendChatMessage(`My plant photo check suggests ${d.condition} on ${d.crop}${sure}. What should I do next?`, "user");
  appendChatMessage(d.advice || "I could not load advice earlier. Ask me what you would like to know about this result.", "assistant", "From your plant photo check · ask follow-up questions below");
  setView("assistant");
  document.getElementById("assistantMessage").focus();
}

function appendChatMessage(text, role, meta = "") {
  const container = document.getElementById("chatMessages");
  const message = document.createElement("div");
  message.className = `chat-message ${role}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = role === "assistant" ? text.replace(/[*#`]/g, "").trim() : text;
  message.appendChild(paragraph);
  if (meta) {
    const metaElement = document.createElement("span");
    metaElement.className = "message-meta";
    metaElement.textContent = meta;
    message.appendChild(metaElement);
  }
  container.appendChild(message);
  container.scrollTop = container.scrollHeight;
  return message;
}

async function handleAssistant(event) {
  event.preventDefault();
  const input = document.getElementById("assistantMessage");
  const message = input.value.trim();
  if (!message) return;
  appendChatMessage(message, "user");
  input.value = "";
  const waiting = appendChatMessage("Reviewing your saved field context…", "assistant", "Dhartisense assistant");
  try {
    const response = await fetch("/api/assistant", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, context: { ...profileContext(), plant_diagnosis: state.lastDiagnosis } }) });
    const payload = await response.json();
    waiting.remove();
    appendChatMessage(payload.answer || "No answer was returned.", "assistant", payload.mode === "groq" ? `Groq · ${payload.model}` : "Configuration and evidence status shown");
    updateAssistantStatus(payload.connected);
  } catch {
    waiting.remove();
    appendChatMessage("The assistant is unavailable right now. Your field profile remains saved on this device.", "assistant", "Local fallback");
  }
}

function updateAssistantStatus(connected) {
  const pill = document.getElementById("assistantStatus");
  const dot = document.getElementById("assistantDot");
  pill.textContent = connected ? "Connected" : "Key required";
  pill.className = `status-pill ${connected ? "green" : "neutral"}`;
  dot.classList.toggle("connected", Boolean(connected));
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    updateAssistantStatus(payload.groq_configured);
    document.getElementById("plantCrop").append(...(payload.disease_crops || []).map((crop) => new Option(crop, crop)));
    fillCropChips(payload.rank_crops || []);
    state.allCrops = payload.rank_crops || [];
    const cropSelect = document.getElementById("fieldCrop");
    const chosen = cropSelect.value;
    cropSelect.innerHTML = '<option value="">Not planted yet</option>' + state.allCrops.map((c) => `<option>${escapeHtml(c)}</option>`).join("");
    cropSelect.value = chosen;
    document.getElementById("waterOtherCrop").append(...state.allCrops.map((crop) => new Option(crop, crop)));
    renderWaterCrops();
  } catch {
    updateAssistantStatus(false);
  }
}

function bindEvents() {
  document.querySelectorAll("[data-view], [data-view-target]").forEach((element) => {
    element.addEventListener("click", () => {
      const target = element.dataset.view || element.dataset.viewTarget;
      if (target) setView(target);
    });
  });
  document.getElementById("setupFirstField").addEventListener("click", startNewField);
  document.getElementById("setupNoticeButton").addEventListener("click", openModal);
  document.getElementById("authForm").addEventListener("submit", submitAuth);
  document.querySelectorAll(".auth-tab").forEach((tab) => tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode)));
  document.getElementById("signOutButton").addEventListener("click", signOut);
  document.getElementById("languageSelect").addEventListener("change", (e) => {
    try { localStorage.setItem(LANG_KEY, e.target.value); } catch { /* kept for this visit only */ }
    applyLanguage();
    toast(e.target.value === "English" ? "Language set to English." : `Language set to ${e.target.value}. Menus, titles and assistant answers now use it; some detailed screens are still in English.`);
  });
  document.getElementById("unitSelect").addEventListener("change", (e) => {
    try { localStorage.setItem(UNITS_KEY, e.target.value); } catch { /* kept for this visit only */ }
    renderAll();
    renderFieldLists();
    toast(e.target.value === "imperial" ? "Units set to acres and °F." : "Units set to hectares and °C.");
  });
  document.getElementById("authForgot").addEventListener("click", forgotPassword);
  document.getElementById("pwToggle").addEventListener("click", (e) => {
    const input = document.getElementById("authPassword");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    e.currentTarget.classList.toggle("on", show);
    e.currentTarget.setAttribute("aria-pressed", String(show));
    e.currentTarget.setAttribute("aria-label", show ? "Hide password" : "Show password");
    input.focus();
  });
  document.getElementById("verifyResend").addEventListener("click", resendVerification);
  document.getElementById("verifyDone").addEventListener("click", () => checkVerified(true));
  document.getElementById("verifyOut").addEventListener("click", signOut);
  document.getElementById("fieldSwitcher").addEventListener("change", (e) => { if (e.target.value === "new") startNewField(); else if (e.target.value !== "draft" && e.target.value) selectField(e.target.value); });
  document.getElementById("fieldList").addEventListener("click", (e) => {
    const card = e.target.closest(".field-card");
    if (!card) return;
    const id = card.dataset.field;
    const del = e.target.closest("[data-field-delete]");
    if (del) return deleteField(id);
    if (state.profile?.id !== id) selectField(id);
    const go = e.target.closest("[data-field-go]");
    if (go) setView(go.dataset.fieldGo);
  });
  document.getElementById("closeModal").addEventListener("click", closeModal);
  document.getElementById("setupModal").addEventListener("click", (event) => { if (event.target.id === "setupModal") closeModal(); });
  document.getElementById("quickLocation").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); searchLocation(); } });
  document.getElementById("quickSetupForm").addEventListener("submit", handleQuickSetup);
  document.getElementById("fieldForm").addEventListener("submit", saveFieldFromForm);
  document.getElementById("undoPoint").addEventListener("click", undoPoint);
  document.getElementById("modeTap").addEventListener("click", () => setDrawMode("tap"));
  document.getElementById("modeFree").addEventListener("click", () => {
    if (state.mapClosed) { toast("Clear the current boundary first, then draw freehand.", "info"); return; }
    setDrawMode("free");
  });
  document.getElementById("finishPolygon").addEventListener("click", closeShape);
  document.getElementById("openFieldLocationSearch").addEventListener("click", () => {
    const panel = document.getElementById("fieldLocationSearch");
    panel.hidden = !panel.hidden;
    if (!panel.hidden) document.getElementById("fieldLocationQuery").focus();
  });
  document.getElementById("fieldLocationSearchButton").addEventListener("click", findFieldPlace);
  document.getElementById("fieldLocationQuery").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); findFieldPlace(); } });
  document.getElementById("clearPolygon").addEventListener("click", clearPolygon);
  document.getElementById("locateMe").addEventListener("click", useCurrentLocation);
  document.getElementById("refreshWeather").addEventListener("click", refreshAll);
  document.getElementById("cropPlanForm").addEventListener("submit", handleCropPlan);
  document.getElementById("planField").addEventListener("change", (e) => { if (e.target.value) selectField(e.target.value); });
  document.getElementById("cropResult").addEventListener("click", (e) => { const b = e.target.closest("[data-grow-crop]"); if (b) toggleGrowing(b.dataset.growCrop); });
  document.getElementById("growingBar").addEventListener("click", (e) => { const b = e.target.closest("[data-grow-remove]"); if (b) toggleGrowing(b.dataset.growRemove); });
  document.getElementById("waterForm").addEventListener("submit", handleWaterForm);
  document.getElementById("waterCrops").addEventListener("click", (e) => { const c = e.target.closest(".choice-chip"); if (!c) return; waterSel.has(c.dataset.crop) ? waterSel.delete(c.dataset.crop) : waterSel.add(c.dataset.crop); renderWaterCrops(); });
  document.getElementById("waterAllCrops").addEventListener("click", () => { (state.lastRank?.options || []).forEach((o) => waterSel.add(o.crop)); renderWaterCrops(); });
  document.getElementById("waterOtherCrop").addEventListener("change", (e) => { if (e.target.value) waterSel.add(e.target.value); e.target.value = ""; renderWaterCrops(); });
  document.getElementById("plantImage").addEventListener("change", handleImage);
  document.getElementById("plantHistory").addEventListener("click", setCheckFeedback);
  document.getElementById("clearHistory").addEventListener("click", () => {
    if (!readChecks().length || !window.confirm("Delete all saved plant checks on this device?")) return;
    writeChecks([]);
    openChecks.clear();
    renderChecks();
    toast("Plant check history cleared.", "info");
  });
  renderChecks();
  document.getElementById("assistantForm").addEventListener("submit", handleAssistant);
  document.getElementById("printReport").addEventListener("click", () => {
    renderReport();
    document.body.classList.add("printing-report");
    setTimeout(() => { window.print(); document.body.classList.remove("printing-report"); }, 700); // let the map tiles load before the print preview opens
  });
  document.getElementById("clearLocalData").addEventListener("click", signOut);
  document.getElementById("mobileMenuButton").addEventListener("click", () => (document.body.classList.contains("nav-open") ? closeNav() : openNav()));
  const backdrop = document.createElement("div");
  backdrop.className = "sidebar-backdrop";
  backdrop.addEventListener("click", closeNav);
  document.body.appendChild(backdrop);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeNav(); });
  window.matchMedia("(min-width: 821px)").addEventListener("change", (e) => { if (e.matches) closeNav(); });
}

document.addEventListener("DOMContentLoaded", () => {
  initialPanels = { crop: document.getElementById("cropResult").innerHTML, water: document.getElementById("waterResult").innerHTML, plant: document.querySelector('[data-view-panel="plant-health"] .result-panel').innerHTML };
  document.getElementById("languageSelect").value = currentLanguage();
  document.getElementById("unitSelect").value = useImperial() ? "imperial" : "metric";
  applyLanguage();
  bindEvents();
  checkHealth();
  startSession();
  iconRefresh();
});
