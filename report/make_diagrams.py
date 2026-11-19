"""Draw the block diagrams used in the report (architecture and flowcharts). No data and no model output is involved.

  python report/make_diagrams.py        -> report/figures/diagrams/*.png
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)
for f in ("times.ttf", "timesbd.ttf", "timesi.ttf"):
    p = Path("C:/Windows/Fonts") / f
    if p.exists():
        font_manager.fontManager.addfont(str(p))
plt.rcParams["font.family"] = "Times New Roman"

GREEN, BLUE, SAND, GREY, ROSE, WHITE = "#DCEBDD", "#D9E6F2", "#F5EBCF", "#E9E9E9", "#F4DCDC", "#FFFFFF"


def canvas(w=6.9, h=4.0, y0=0, y1=100):
    fig, ax = plt.subplots(figsize=(w, h), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(y0, y1)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc=WHITE, fs=8.5, bold=False, wrap=None, ec="#333333", lw=0.9, style="round,pad=0.25,rounding_size=1.2", align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw))
    if wrap:
        text = "\n".join(textwrap.fill(line, wrap) for line in text.split("\n"))
    t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.15, multialignment=align)
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    for _ in range(40):  # shrink until the text sits inside the box with a small margin
        bb = t.get_window_extent(renderer)
        (x0, y0), (x1, y1) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
        if x1 - x0 <= w - 1.6 and y1 - y0 <= h - 1.0:
            break
        t.set_fontsize(t.get_fontsize() - 0.2)


def group(ax, x, y, w, h, title, fc=GREY, fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.5", fc=fc, ec="#555555", lw=1.0, ls="-"))
    ax.text(x + 1.2, y + h - 1.0, title, ha="left", va="top", fontsize=fs, fontweight="bold")


def arrow(ax, p, q, label=None, fs=7.5, both=False, rad=0.0, lo=(0, 0.9), color="#222222"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=9, lw=0.9, color=color, connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))
    if label:
        ax.text((p[0] + q[0]) / 2 + lo[0], (p[1] + q[1]) / 2 + lo[1], label, ha="center", va="bottom", fontsize=fs, style="italic", color="#222222",
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", pad_inches=0.06, facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------------------------------- 1 architecture
def architecture():
    fig, ax = canvas(6.9, 4.9)
    group(ax, 1, 44, 30, 52, "Browser (no build step)", BLUE)
    for i, t in enumerate(["Leaflet map and drawing\n(fields, NDVI colours)", "Crop plan, Water and nutrients,\nPlant health, Assistant, Reports", "Field plan layout, calendar (.ics)\n5 languages, units", "Firebase web sign-in (direct\nto Firebase Authentication)"]):
        box(ax, 3, 80 - i * 10.4, 26, 8.4, t, WHITE, fs=7.6)
    group(ax, 38, 30, 31, 66, "Python server (standard library)", GREEN)
    box(ax, 40, 83, 27, 7.5, "Routes, sessions, rate limits,\nsecurity headers (server.py)", WHITE, fs=7.6)
    box(ax, 40, 72, 27, 8, "Crop ranking\nml/crop_fit.py", SAND, fs=7.8)
    box(ax, 40, 62, 27, 8, "Irrigation (FAO-56)\nml/water_plan.py", SAND, fs=7.8)
    box(ax, 40, 52, 27, 8, "Fertiliser plan\nml/nutrient_plan.py", SAND, fs=7.8)
    box(ax, 40, 42, 27, 8, "Crop health (NDVI)\napp/ndvi.py", SAND, fs=7.8)
    box(ax, 40, 32, 27, 8, "Plant photo check\nConvNeXt-Tiny + vision model", SAND, fs=7.6)
    group(ax, 76, 62, 23, 34, "Firebase", ROSE)
    box(ax, 78, 80, 19, 8, "Authentication\n(email, verification)", WHITE, fs=7.6)
    box(ax, 78, 66, 19, 8.5, "Firestore\nusers/{uid}/fields/{id}", WHITE, fs=7.6)
    group(ax, 76, 6, 23, 52, "External services", GREY)
    for i, t in enumerate(["Open-Meteo\nforecast and history", "Planetary Computer\nSentinel-2 L2A", "Groq\nassistant, vision", "Esri imagery,\nNominatim, Photon"]):
        box(ax, 78, 44 - i * 11.2, 19, 9, t, WHITE, fs=7.4)
    group(ax, 1, 6, 67, 20, "Data files built offline (not in the repository)", GREY, fs=8.5)
    box(ax, 3, 8, 20, 11, "crop_requirements.json\n(38 crops, FAO EcoCrop)", WHITE, fs=7.2)
    box(ax, 25, 8, 20, 11, "regional_crops.json\n(484 districts)", WHITE, fs=7.2)
    box(ax, 47, 8, 19, 11, "plant_disease_v3.pth\n(trained in Colab)", WHITE, fs=7.2)
    arrow(ax, (31, 74), (38, 74), "HTTPS + cookie", both=True, lo=(0, 1.0))
    arrow(ax, (69, 73), (76, 73), "Admin SDK", both=True, lo=(0, 1.0))
    arrow(ax, (69, 45), (76, 35), "HTTPS APIs", both=True, lo=(0, 1.0))
    arrow(ax, (53, 26), (53, 31.5), None)
    save(fig, "architecture")


# ----------------------------------------------------------------------------------------- 2 session
def session():
    fig, ax = canvas(6.9, 3.6)
    xs = {"Browser": 12, "Firebase Auth": 40, "Dhartisense server": 68, "Firestore": 91}
    for name, x in xs.items():
        box(ax, x - 9, 47, 18, 6, name, GREEN if name != "Firestore" else ROSE, fs=8.5, bold=True)
        ax.plot([x, x], [3, 47], color="#888888", lw=0.8, ls=(0, (3, 3)))
    steps = [("Browser", "Firebase Auth", "1  email + password", 42), ("Firebase Auth", "Browser", "2  ID token (verified email)", 36), ("Browser", "Dhartisense server", "3  POST /api/auth/session", 30),
             ("Dhartisense server", "Firebase Auth", "4  verify token, check recent sign-in", 24), ("Dhartisense server", "Browser", "5  HttpOnly session cookie (14 days)", 18),
             ("Browser", "Dhartisense server", "6  API call with cookie", 12), ("Dhartisense server", "Firestore", "7  read or write users/{uid}/fields", 6)]
    for a, b, t, y in steps:
        arrow(ax, (xs[a], y), (xs[b], y), t, lo=(0, 0.8), fs=7.6)
    save(fig, "session")


# ----------------------------------------------------------------------------------------- 3 crop ranking pipeline
def crop_pipeline():
    fig, ax = canvas(6.9, 3.4, 0, 62)
    box(ax, 1, 40, 17, 14, "Saved field:\nlocation, pH, soil texture,\nwater source", BLUE, fs=7.8)
    box(ax, 1, 20, 17, 12, "Planting date and\nobjective (fit, risk, water)", BLUE, fs=7.8)
    box(ax, 24, 42, 20, 16, "Weather history\nOpen-Meteo archive,\nlast 6 years (daily mean\ntemperature, rain)", GREY, fs=7.6)
    box(ax, 24, 18, 20, 16, "Season window per year:\nstart on planting date,\nlength = crop cycle", SAND, fs=7.6)
    box(ax, 50, 42, 20, 16, "Fit per factor\n(temperature, rain,\npH, texture)\nEcoCrop ranges", GREEN, fs=7.6)
    box(ax, 50, 18, 20, 16, "Weighted geometric mean\n2 : 2 : 1 : 1\n(zero if any factor is zero)", GREEN, fs=7.6)
    box(ax, 76, 42, 22, 16, "5 nearest districts:\nshare of area and yield\n(India, 2008-2015)", GREY, fs=7.6)
    box(ax, 76, 18, 22, 16, "Blend, rule-outs, label\nGood / Fair / Weak match\nTop 5 crops", GREEN, fs=7.6)
    box(ax, 50, 2, 20, 10, "Irrigation need from the\nFAO-56 water balance", SAND, fs=7.4)
    arrow(ax, (18, 47), (24, 50)); arrow(ax, (18, 26), (24, 26)); arrow(ax, (44, 50), (50, 50)); arrow(ax, (34, 42), (34, 34))
    arrow(ax, (44, 26), (50, 26)); arrow(ax, (60, 42), (60, 34)); arrow(ax, (70, 26), (76, 26)); arrow(ax, (87, 42), (87, 34))
    arrow(ax, (60, 12), (60, 18), None, rad=0)
    arrow(ax, (70, 7), (87, 18), None, rad=0.1)
    save(fig, "crop_pipeline")


# ----------------------------------------------------------------------------------------- 4 water balance loop
def water_loop():
    fig, ax = canvas(6.9, 3.4, 4, 90)
    box(ax, 1, 66, 20, 20, "Inputs per day\nET0 and rain (Open-Meteo)\nplanting date, crop,\nsoil texture, method", BLUE, fs=7.8)
    box(ax, 28, 66, 20, 20, "Stage and Kc\nroot depth Zr(t)\nTAW = AWC x Zr\nRAW = min(p x TAW, cap)", SAND, fs=7.8)
    box(ax, 55, 66, 20, 20, "Water use\nETc = Kc x ET0\neffective rain\n0.8 x P if P >= 3 mm", SAND, fs=7.8)
    box(ax, 80, 66, 19, 20, "Depletion\nD = max(0, D + ETc\n- effective rain)", GREEN, fs=7.8)
    box(ax, 80, 36, 19, 18, "D >= RAW?\nStressed crop", WHITE, fs=8.5, bold=True, style="round,pad=0.25,rounding_size=6")
    box(ax, 55, 36, 20, 18, "Rain in next 3 days\nfills 60% of D?\nthen wait for rain", ROSE, fs=7.8)
    box(ax, 28, 36, 20, 18, "Irrigate: net = D\ngross = net / efficiency\n(drip 0.90 ... flood 0.55)", GREEN, fs=7.8)
    box(ax, 1, 36, 20, 18, "Output: status, date,\ndepth, next rounds,\ncalendar reminders", BLUE, fs=7.8)
    box(ax, 28, 8, 47, 16, "Farmer's own information overrides the model:\nlast irrigation date and how the soil surface looks today\n(dry and dusty ... standing water)", GREY, fs=8)
    arrow(ax, (21, 76), (28, 76)); arrow(ax, (48, 76), (55, 76)); arrow(ax, (75, 76), (80, 76)); arrow(ax, (89.5, 66), (89.5, 54))
    arrow(ax, (80, 45), (75, 45), "yes"); arrow(ax, (55, 45), (48, 45), "no rain"); arrow(ax, (28, 45), (21, 45))
    arrow(ax, (38, 24), (38, 36), None, lo=(0, 0))
    ax.text(89.5, 28, "no: step to\nthe next day", ha="center", fontsize=7.6, style="italic")
    save(fig, "water_loop")


# ----------------------------------------------------------------------------------------- 5 disease cascade
def disease_flow():
    fig, ax = canvas(6.9, 3.6, 20, 96)
    box(ax, 1, 78, 20, 14, "Farmer photo\n(max 8 MB, 25 MP)\n+ crop chosen", BLUE, fs=8)
    box(ax, 28, 78, 20, 14, "Resize, centre crop 288 px\nflip-averaged logits\ndivided by temperature T", SAND, fs=7.6)
    box(ax, 55, 78, 20, 14, "Mask to the chosen\ncrop's classes\nsoftmax, top 3", SAND, fs=7.8)
    box(ax, 80, 78, 19, 14, "Top-1 probability\n>= threshold\n(at least 0.85)?", WHITE, fs=7.8, bold=False, style="round,pad=0.25,rounding_size=5")
    box(ax, 80, 52, 19, 14, "Show disease,\nconfidence, top 3\nand cure steps", GREEN, fs=7.8)
    box(ax, 55, 52, 20, 14, "Unsure, or the crop\nhas only a healthy\nclass in the model", ROSE, fs=7.8)
    box(ax, 28, 52, 20, 14, "Vision language model\n(Groq): symptoms,\nup to 3 causes,\n3 questions", SAND, fs=7.6)
    box(ax, 1, 52, 20, 14, "Farmer answers\nthe questions", BLUE, fs=7.8)
    box(ax, 28, 26, 20, 14, "Advice text: What it is,\nCure, Prevention,\nSee an expert if", GREEN, fs=7.6)
    box(ax, 55, 26, 44, 14, "Always shown: \"likely classification aid, not a confirmed diagnosis\"\nIf neither engine answers, the app says so instead of guessing", GREY, fs=7.8)
    box(ax, 1, 26, 20, 14, "Saved history\nin the field record", BLUE, fs=7.8)
    arrow(ax, (21, 85), (28, 85)); arrow(ax, (48, 85), (55, 85)); arrow(ax, (75, 85), (80, 85)); arrow(ax, (89.5, 78), (89.5, 66), "yes")
    arrow(ax, (80, 82), (75, 59), "no", rad=-0.0, lo=(-1.5, 0)); arrow(ax, (55, 59), (48, 59)); arrow(ax, (28, 59), (21, 59)); arrow(ax, (11, 52), (28, 40), None, rad=0.15)
    arrow(ax, (38, 52), (38, 40)); arrow(ax, (89.5, 52), (89.5, 40), None); arrow(ax, (28, 33), (21, 33))
    save(fig, "disease_flow")


# ----------------------------------------------------------------------------------------- 6 NDVI pipeline
def ndvi_flow():
    fig, ax = canvas(6.9, 2.9, 4, 74)
    box(ax, 1, 52, 17, 18, "Field boundary\n(GeoJSON polygon,\nat least 1000 m2)", BLUE, fs=7.8)
    box(ax, 24, 52, 19, 18, "STAC search\nSentinel-2 L2A, last 150 days\nscene cloud < 60%\none scene per day", GREY, fs=7.4)
    box(ax, 49, 52, 22, 18, "Statistics endpoint\nNDVI = (B08 - B04)/(B08 + B04)\nmean, min, max, std,\nhistogram over the polygon", SAND, fs=7.4)
    box(ax, 77, 52, 22, 18, "Scene classification layer\nbad classes: saturated, shadow,\ncloud, cirrus, snow\nusable if bad share < 20%", SAND, fs=7.4)
    box(ax, 77, 22, 22, 18, "Summary: latest reading,\nchange vs. earlier scene\n(>= 5 days apart),\nweak / moderate / strong share", GREEN, fs=7.4)
    box(ax, 49, 22, 22, 18, "Plain-language notes\n(decline of 0.10 or more,\nweak area, uneven field)", GREEN, fs=7.6)
    box(ax, 24, 22, 19, 18, "Browser colour map\nfrom the same service's\ntile endpoint", BLUE, fs=7.6)
    box(ax, 1, 22, 17, 18, "Saved on the field:\nlatest reading in the\ncard and report", BLUE, fs=7.6)
    arrow(ax, (18, 61), (24, 61)); arrow(ax, (43, 61), (49, 61)); arrow(ax, (71, 61), (77, 61)); arrow(ax, (88, 52), (88, 40)); arrow(ax, (77, 31), (71, 31)); arrow(ax, (49, 31), (43, 31)); arrow(ax, (24, 31), (18, 31))
    ax.text(50, 8, "Results are cached for 6 hours per boundary; scenes are read in parallel (8 workers).", ha="center", fontsize=8, style="italic")
    save(fig, "ndvi_flow")


# ----------------------------------------------------------------------------------------- 7 fertiliser flow
def nutrient_flow():
    fig, ax = canvas(6.9, 2.4, 4, 66)
    box(ax, 1, 40, 18, 22, "Soil-test values\nN, P, K in kg/ha\n(typed by farmer,\nmay be blank)", BLUE, fs=7.8)
    box(ax, 25, 40, 20, 22, "Rate each nutrient\nSoil Health Card limits\nlow / medium / high /\nunknown", SAND, fs=7.8)
    box(ax, 51, 40, 22, 22, "Adjust crop dose\nlow x 1.25, medium x 1,\nhigh x 0.75, unknown x 1\n(general dose: N, P2O5, K2O)", SAND, fs=7.6)
    box(ax, 79, 40, 20, 22, "Fertiliser amounts\nDAP, urea, MOP\nper hectare and\nfor the whole field", GREEN, fs=7.8)
    box(ax, 51, 8, 22, 20, "Split nitrogen\n50 / 25 / 25 over the season\n(legumes: all at sowing;\nlong crops: 4 x 25%)", GREEN, fs=7.6)
    box(ax, 79, 8, 20, 20, "Dates from the\nplanting date,\nnote if dose is\n\"checked\" or indicative", BLUE, fs=7.6)
    arrow(ax, (19, 51), (25, 51)); arrow(ax, (45, 51), (51, 51)); arrow(ax, (73, 51), (79, 51)); arrow(ax, (62, 40), (62, 28)); arrow(ax, (73, 18), (79, 18))
    save(fig, "nutrient_flow")


# ----------------------------------------------------------------------------------------- 8 deployment
def deployment():
    fig, ax = canvas(6.9, 3.5)
    group(ax, 1, 8, 24, 80, "Developer machine", BLUE)
    box(ax, 3, 62, 20, 14, "Repository\n(code, docs, no secrets)", WHITE, fs=7.8)
    box(ax, 3, 42, 20, 14, "build_bundle.py\nclean bundle in build/", SAND, fs=7.8)
    box(ax, 3, 22, 20, 14, "Local data files\n(git-ignored)", WHITE, fs=7.8)
    group(ax, 33, 8, 34, 80, "Host (Docker container)", GREEN)
    box(ax, 35, 62, 30, 14, "Dockerfile: Python 3.12,\nnon-root user, port from PORT", WHITE, fs=7.8)
    box(ax, 35, 42, 30, 14, "Server + browser app +\n2 data files (+ model, optional)", SAND, fs=7.8)
    box(ax, 35, 22, 30, 14, "Render blueprint (free) or\nGoogle Cloud Run (custom domain)", WHITE, fs=7.8)
    group(ax, 75, 8, 24, 80, "Managed services", ROSE)
    box(ax, 77, 62, 20, 14, "Firebase Auth\n+ Firestore rules\n(deny all browsers)", WHITE, fs=7.6)
    box(ax, 77, 42, 20, 14, "Groq, Open-Meteo,\nPlanetary Computer", WHITE, fs=7.6)
    box(ax, 77, 22, 20, 14, "HTTPS, secure\ncookie, HSTS", WHITE, fs=7.8)
    arrow(ax, (23, 49), (35, 49)); arrow(ax, (65, 69), (77, 69), both=True); arrow(ax, (65, 49), (77, 49), both=True)
    save(fig, "deployment")


# ----------------------------------------------------------------------------------------- 9 farmer workflow
def workflow():
    fig, ax = canvas(6.9, 2.9, 0, 66)
    steps = ["1  Create account\nconfirm email", "2  Map the field\nboundary, soil, water", "3  Crop plan\ntop 5 crops, pick", "4  Water and\nnutrients plan", "5  Crop health\nsatellite NDVI", "6  Plant health\nphoto check", "7  Report\nprint or PDF"]
    cols = [BLUE, GREEN, SAND, SAND, GREEN, ROSE, BLUE]
    pos = [(1, 38), (26, 38), (51, 38), (76, 38), (1, 14), (26, 14), (51, 14)]
    for (x, y), t_, c in zip(pos, steps, cols):
        box(ax, x, y, 22, 18, t_, c, fs=9.5)
    for i in (0, 1, 2):
        arrow(ax, (pos[i][0] + 22, 47), (pos[i + 1][0], 47))
    for i in (4, 5):
        arrow(ax, (pos[i][0] + 22, 23), (pos[i + 1][0], 23))
    ax.text(88.5, 23, "The assistant can be\nasked at any step and\nreceives the field context.", ha="center", va="center", fontsize=8.2, style="italic")
    save(fig, "workflow")


if __name__ == "__main__":
    for fn in (architecture, session, crop_pipeline, water_loop, disease_flow, ndvi_flow, nutrient_flow, deployment, workflow):
        fn()
    print("diagrams written to", OUT)
