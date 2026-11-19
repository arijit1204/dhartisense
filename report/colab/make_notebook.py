"""Writes dhartisense_report_figures.ipynb. The plant-data and training cells are copied from ml/training/train_plant_disease_v3_colab.ipynb so they stay identical.

  python report/colab/make_notebook.py
"""
import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = json.loads((HERE.parent.parent / "ml" / "training" / "train_plant_disease_v3_colab.ipynb").read_text(encoding="utf8"))
orig = ["".join(c["source"]) for c in SRC["cells"]]
cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(True)})


md("""
# Dhartisense report figures (Colab)

Produces the machine-learning graphs of the project report. Nothing here changes the application.

| Section | Needs | Makes (file name = figure key) |
|---|---|---|
| A. Engine figures | uploads of `ml/*.py` and the two JSON files | `c_tfit`, `c_kc`, `c_water`, `c_regional` |
| B. Crop-ranking benchmark | same uploads, internet (Open-Meteo), about 10 minutes | `c_bench`, `c_floor` |
| C. Plant model evaluation | GPU, `plant_disease_v3.pth` upload, Kaggle datasets | `c_classes`, `c_perclass`, `c_reliab`, `c_cov`, `c_cm` |
| D. Plant model re-run (optional) | GPU, about 30 minutes | `c_curve` |

**Before running:** Runtime > Change runtime type > **T4 GPU**. Run the sections in order. At the end a zip of all images downloads: copy the PNG files into `report/figures/colab/` and run `python report/build_report.py`.
""")

code("""
!pip -q install kagglehub
import json, math, random, sys, datetime as dt
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

OUT = Path('/content/report_figures'); OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Liberation Serif', 'DejaVu Serif'], 'font.size': 10,
                     'axes.grid': True, 'grid.alpha': 0.3, 'axes.spines.top': False, 'axes.spines.right': False})

def save(fig, name):
    fig.savefig(OUT / f'{name}.png', dpi=200, bbox_inches='tight')
    plt.show()
    print('saved', name)
""")

md("## A. Engine figures")
code("""
from google.colab import files
PROJ = Path('/content/proj'); (PROJ / 'ml' / 'models').mkdir(parents=True, exist_ok=True)
(PROJ / 'ml' / '__init__.py').write_text('')
print('Select together: crop_fit.py, water_plan.py, nutrient_plan.py, crop_requirements.json, regional_crops.json')
for name, data in files.upload().items():
    (PROJ / 'ml' / ('models' if name.endswith('.json') else '') / name).write_bytes(data)
sys.path.insert(0, str(PROJ))
from ml import crop_fit, water_plan, nutrient_plan
print(len(crop_fit.CROPS), 'crops;', len(crop_fit.REGIONAL), 'districts')
""")

md("### c_tfit: trapezoid and centred fit")
code("""
CROP = 'Wheat'   # any crop name from crop_fit.CROPS
c = next(x for x in crop_fit.CROPS if x['name'] == CROP)
x1, x2, x3, x4 = c['TMIN'], c['TOPMN'], c['TOPMX'], c['TMAX']
xs = np.linspace(x1 - 4, x4 + 4, 800)
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.plot(xs, [crop_fit.trapezoid(x, x1, x2, x3, x4) for x in xs], label='T(x), trapezoid')
ax.plot(xs, [crop_fit.centred(x, x1, x2, x3, x4) for x in xs], '--', label='C(x), centred')
for v, t in zip((x1, x2, x3, x4), ('$x_1$', '$x_2$', '$x_3$', '$x_4$')):
    ax.axvline(v, color='grey', lw=0.8, ls=':'); ax.text(v, 1.05, t, ha='center')
ax.set_ylim(0, 1.15); ax.set_xlabel(f'Daily mean temperature (°C), {CROP}'); ax.set_ylabel('Fit score'); ax.legend(loc='lower center')
save(fig, 'c_tfit')
""")

md("### c_kc: crop coefficient and root depth")
code("""
fig, (a, b) = plt.subplots(1, 2, figsize=(9, 3.4))
for n in ('Rice', 'Wheat', 'Maize'):
    crop = water_plan.CROP_WATER[n]; L = sum(crop[3])
    st = [water_plan.stage_info(crop, int(t)) for t in range(L)]
    a.plot(range(L), [s[1] for s in st], label=n); b.plot(range(L), [s[2] for s in st], label=n)
a.set_xlabel('Days after planting'); a.set_ylabel('Crop coefficient $K_c$'); a.legend()
b.set_xlabel('Days after planting'); b.set_ylabel('Root depth $Z_r$ (m)')
save(fig, 'c_kc')
""")

md("### c_water: depletion and irrigation rounds with real past weather")
code("""
import urllib.request, urllib.parse
LAT, LON = 12.52, 76.90          # a sample point near Mandya, Karnataka; put your own field here
PLANTING = dt.date(2025, 11, 1)  # a past date so that the archive has the whole season
q = urllib.parse.urlencode({'latitude': LAT, 'longitude': LON, 'timezone': 'auto', 'daily': 'et0_fao_evapotranspiration,precipitation_sum',
                            'start_date': PLANTING.isoformat(), 'end_date': (PLANTING + dt.timedelta(125)).isoformat()})
with urllib.request.urlopen('https://archive-api.open-meteo.com/v1/archive?' + q, timeout=60) as r:
    daily = json.loads(r.read())['daily']
weather = {dt.date.fromisoformat(d): (e, p or 0.0) for d, e, p in zip(daily['time'], daily['et0_fao_evapotranspiration'], daily['precipitation_sum']) if e is not None}
crop = water_plan.CROP_WATER['Wheat']
rows, _ = water_plan.simulate(crop, PLANTING, weather, water_plan.AWC['loam'], water_plan.EFFICIENCY['sprinkler'], PLANTING, 0.0, True, PLANTING + dt.timedelta(125), water_plan.MAX_NET['sprinkler'])
day = [(r['date'] - PLANTING).days for r in rows]
peak = [r['depletion'] + r['irrigated_net'] for r in rows]
fig, ax = plt.subplots(figsize=(7, 3.6))
ax.plot(day, peak, label='Depletion $D$ (before irrigation)')
ax.step(day, [r['raw'] for r in rows], where='mid', color='crimson', ls='--', label='RAW (irrigate when $D \\\\geq$ RAW)')
ax.scatter([d for d, r in zip(day, rows) if r['irrigated_net']], [p for p, r in zip(peak, rows) if r['irrigated_net']], color='black', zorder=3, label='Irrigation')
ax.set_xlabel('Days after planting'); ax.set_ylabel('Depletion (mm)')
ax2 = ax.twinx(); ax2.bar(day, [r['rain'] for r in rows], color='tab:blue', alpha=0.4, label='Rain'); ax2.set_ylabel('Rain (mm/day)'); ax2.set_ylim(0, max(60, 3 * max(r['rain'] for r in rows))); ax2.grid(False)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=8)
ax.set_title(f'Wheat, loam, sprinkler, planted {PLANTING} at ({LAT}, {LON}): {sum(1 for r in rows if r["irrigated_net"])} irrigations', fontsize=9)
save(fig, 'c_water')
""")

md("### c_regional: district centres in the regional data")
code("""
R = crop_fit.REGIONAL
n_seasons = np.array([len(d['seasons']) for d in R])
fig, ax = plt.subplots(figsize=(5.2, 5.6))
sc = ax.scatter([d['lon'] for d in R], [d['lat'] for d in R], c=n_seasons, s=9, cmap='viridis')
cb = fig.colorbar(sc, ax=ax, ticks=[1, 2, 3]); cb.set_label('Seasons with data')
ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude'); ax.set_title(f'{len(R)} districts in {len({d["state"] for d in R})} states', fontsize=10)
save(fig, 'c_regional')
""")

md("""
## B. Crop-ranking benchmark
Same protocol as `ml/training/benchmark_crop_fit.py`: 120 random districts, development and test halves, five variants. Weather history for each district is fetched from Open-Meteo (about 4 seconds each, so roughly 10 minutes).
""")
code("""
import time, urllib.request, urllib.parse, collections
SEASONS = {'Kharif': (6, 25, False), 'Rabi': (11, 5, True)}   # sowing date, whether irrigation is assumed
N_DISTRICTS = 120

def weather_history(lat, lon):
    end = dt.date.today() - dt.timedelta(days=3)
    q = urllib.parse.urlencode({'latitude': lat, 'longitude': lon, 'timezone': 'auto', 'daily': 'temperature_2m_mean,precipitation_sum',
                                'start_date': (end - dt.timedelta(days=6 * 365)).isoformat(), 'end_date': end.isoformat()})
    with urllib.request.urlopen('https://archive-api.open-meteo.com/v1/archive?' + q, timeout=60) as r:
        daily = json.loads(r.read())['daily']
    return {dt.date.fromisoformat(d): (t, p or 0.0) for d, t, p in zip(daily['time'], daily['temperature_2m_mean'], daily['precipitation_sum']) if t is not None}

ok = [d for d in crop_fit.REGIONAL if all(s in d['seasons'] for s in SEASONS)]
random.Random(7).shuffle(ok)
districts = sorted(ok[:N_DISTRICTS], key=lambda d: (d['state'], d['district']))
weather = {}
for i, d in enumerate(districts):
    key = f"{d['state']}|{d['district']}"
    for attempt in range(3):
        try:
            weather[key] = weather_history(d['lat'], d['lon']); break
        except Exception as e:
            time.sleep(5 * (attempt + 1))
    if i % 10 == 0: print('weather', i, 'of', len(districts), flush=True)
print(len(weather), 'districts with weather')
""")
code("""
def evaluate(floor):
    national = {s: collections.Counter() for s in SEASONS}
    for d in crop_fit.REGIONAL:
        for s in SEASONS:
            for c, (share, _) in d['seasons'].get(s, {}).items():
                national[s][c] += share
    names = [c['name'] for c in crop_fit.CROPS]
    rng = random.Random(1)
    keyed = [d for d in districts if f"{d['state']}|{d['district']}" in weather]
    out = {}
    for split, ds in (('dev', keyed[::2]), ('test', keyed[1::2])):
        tot = collections.defaultdict(lambda: [0.0, 0.0, 0])
        for d in ds:
            days = weather[f"{d['state']}|{d['district']}"]
            for season, (month, dd, irrigated) in SEASONS.items():
                truth = {c: v[0] for c, v in d['seasons'][season].items()}
                top3 = {c for c, _ in sorted(truth.items(), key=lambda x: -x[1])[:3]}
                planting = dt.date(2026, month, dd)
                near = crop_fit.nearby(d['lat'], d['lon'], season, skip=(d['state'], d['district']))
                picks = {
                    'fit only': [o['crop'] for o in crop_fit.rank(days, planting, 'fit', irrigated=irrigated)['options']],
                    'fit + nearby': [o['crop'] for o in crop_fit.rank(days, planting, 'fit', irrigated=irrigated, regional=near, fit_floor=floor)['options']],
                    'nearby only': [c for c, _ in sorted(near['crops'].items(), key=lambda x: -x[1]['share'])[:5]] if near else [],
                    'national': [c for c, _ in national[season].most_common(5)],
                    'random': rng.sample(names, 5),
                }
                for who, p in picks.items():
                    tot[who][0] += len(top3 & set(p)) / 3
                    tot[who][1] += sum(truth.get(c, 0) for c in p)
                    tot[who][2] += 1
        for who, (hit, cover, n) in tot.items():
            out[(split, who)] = (hit / n, cover / n, n)
    return out

FLOORS = [0.0, 0.3, 0.5, 0.7, 0.9]
results = {f: evaluate(f) for f in FLOORS}
VARIANTS = ['fit only', 'fit + nearby', 'nearby only', 'national', 'random']
for f in FLOORS:
    print(f'\\nFIT_FLOOR = {f}')
    for split in ('dev', 'test'):
        for who in VARIANTS:
            h, cv, n = results[f][(split, who)]
            print(f'  {split:4} {who:13} top-3 hit rate {h:6.1%}   cropped area covered {cv:6.1%}   n={n}')
best = max(FLOORS, key=lambda f: results[f][('dev', 'fit + nearby')][0])
print('\\nbest FIT_FLOOR on the development half:', best, '| value in crop_fit.py:', crop_fit.FIT_FLOOR)
""")
code("""
F0 = crop_fit.FIT_FLOOR if crop_fit.FIT_FLOOR in results else best
fig, ax = plt.subplots(figsize=(6.6, 3.5)); w = 0.38; x = np.arange(len(VARIANTS))
for k, (split, col) in enumerate((('dev', 'tab:gray'), ('test', 'tab:green'))):
    v = [results[F0][(split, who)][0] * 100 for who in VARIANTS]
    bars = ax.bar(x + (k - 0.5) * w, v, w, label={'dev': 'Development half', 'test': 'Test half'}[split], color=col)
    ax.bar_label(bars, fmt='%.1f', fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(VARIANTS); ax.set_ylabel('Real top-3 crops found\\nin the 5 suggestions (%)'); ax.legend()
ax.set_title(f'Blending constant = {F0}', fontsize=9)
save(fig, 'c_bench')

fig, ax = plt.subplots(figsize=(5.2, 3.3))
ax.plot(FLOORS, [results[f][('dev', 'fit + nearby')][0] * 100 for f in FLOORS], 'o-', label='Combined, development half')
ax.plot(FLOORS, [results[f][('test', 'fit + nearby')][0] * 100 for f in FLOORS], 's--', label='Combined, test half')
ax.axhline(results[F0][('dev', 'national')][0] * 100, color='grey', ls=':', label='National baseline (dev)')
ax.set_xlabel('Blending constant $\\\\phi$'); ax.set_ylabel('Hit rate (%)'); ax.legend(fontsize=8)
save(fig, 'c_floor')
""")

md("""
## C. Plant model: evaluate the served checkpoint
Rebuilds the data exactly as the training notebook does (cells copied from it), then evaluates `plant_disease_v3.pth`. The numbers printed here should match `plant_disease_v3.metrics.json` (crop unknown: top-1 0.671, top-3 0.913; farmer picks crop: top-1 0.774, top-3 0.960).
""")
code(orig[1])
code(orig[2])
code(orig[3])
code(orig[4])
code("""
import torch, torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import convnext_tiny
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Upload plant_disease_v3.pth')
up = files.upload(); ck = torch.load(next(iter(up)), map_location='cpu', weights_only=True)
CK_LABELS = ck['labels']; SIZE = ck['image_size']; T = float(ck['temperature']); thr, thr_crop = float(ck['threshold']), float(ck['threshold_crop'])
print('classes', len(CK_LABELS), '| temperature', T, '| thresholds', thr, thr_crop)
remap = {ids[l]: CK_LABELS.index(l) for l in labels if l in CK_LABELS}   # data ids -> checkpoint ids
norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
plain = transforms.Compose([transforms.Resize(int(SIZE * 1.14)), transforms.CenterCrop(SIZE), transforms.ToTensor(), norm])   # identical to server.py
class Imgs(Dataset):
    def __init__(self, data): self.data = data
    def __len__(self): return len(self.data)
    def __getitem__(self, i):
        img, y = self.data[i]; return plain(img), remap[y]
net = convnext_tiny(weights=None); net.classifier[2] = nn.Linear(net.classifier[2].in_features, len(CK_LABELS)); net.load_state_dict(ck['state_dict']); net.to(device).eval()
def collect(data):
    out, ys = [], []
    with torch.no_grad():
        for x, y in DataLoader(Imgs(data), batch_size=64):
            x = x.to(device); out.append(((net(x) + net(x.flip(-1))) / 2).float().cpu()); ys.append(y)
    return torch.cat(out), torch.cat(ys)
test_logits, test_y = collect(test_data)
crop_of = [l.split('|')[0] for l in CK_LABELS]
def only_true_crop(lg, ys):
    keep = torch.tensor([[crop_of[c] == crop_of[y] for c in range(len(CK_LABELS))] for y in ys.tolist()])
    return lg.masked_fill(~keep, float('-inf'))
named = only_true_crop(test_logits, test_y)
for tag, lg in (('crop unknown', test_logits), ('farmer picks crop', named)):
    p = F.softmax(lg / T, 1); conf, pred = p.max(1)
    print(f'{tag:18} top-1 {(pred == test_y).float().mean():.3f}  top-3 {(p.topk(3, 1).indices == test_y[:, None]).any(1).float().mean():.3f}  n={len(test_y)}')
""")
md("### c_classes, c_perclass")
code("""
order = sorted(CK_LABELS, key=lambda l: -(n_pd[l] + n_pv[l]))
fig, ax = plt.subplots(figsize=(6.6, 8))
y = np.arange(len(order))
ax.barh(y, [n_pd[l] for l in order], label='PlantDoc (field photos)', color='tab:green')
ax.barh(y, [n_pv[l] for l in order], left=[n_pd[l] for l in order], label='PlantVillage (capped at 100)', color='tab:gray')
ax.set_yticks(y); ax.set_yticklabels([l.replace('|', ': ') for l in order], fontsize=7); ax.invert_yaxis(); ax.set_xlabel('Training images'); ax.legend(loc='lower right')
save(fig, 'c_classes')

pred_all = test_logits.argmax(1)
rows_ = [(CK_LABELS[i], float((pred_all[test_y == i] == i).float().mean()), int((test_y == i).sum())) for i in range(len(CK_LABELS)) if (test_y == i).any()]
rows_.sort(key=lambda r: r[1])
fig, ax = plt.subplots(figsize=(6.6, 6.2))
ax.barh(range(len(rows_)), [r[1] * 100 for r in rows_], color=['crimson' if r[1] < 0.5 else 'tab:green' for r in rows_])
ax.set_yticks(range(len(rows_))); ax.set_yticklabels([f"{r[0].replace('|', ': ')} (n={r[2]})" for r in rows_], fontsize=7)
ax.set_xlabel('Top-1 accuracy on the PlantDoc test split (%)'); ax.set_xlim(0, 105)
save(fig, 'c_perclass')
""")
md("### c_reliab, c_cov, c_cm")
code("""
def reliability(lg, temp, bins=10):
    conf, pred = F.softmax(lg / temp, 1).max(1); right = (pred == test_y).float(); xs, ys = [], []
    for lo in np.linspace(0, 1, bins + 1)[:-1]:
        m = (conf > lo) & (conf <= lo + 1 / bins)
        if m.sum() >= 3: xs.append(float(conf[m].mean())); ys.append(float(right[m].mean()))
    return xs, ys
fig, ax = plt.subplots(figsize=(4.6, 4.4))
ax.plot([0, 1], [0, 1], 'k:', label='Perfect calibration')
ax.plot(*reliability(test_logits, 1.0), 'o-', label='Before (T = 1)')
ax.plot(*reliability(test_logits, T), 's-', label=f'After (T = {T})')
ax.set_xlabel('Mean confidence in bin'); ax.set_ylabel('Accuracy in bin'); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.legend(fontsize=8)
save(fig, 'c_reliab')

fig, ax = plt.subplots(figsize=(6.2, 3.6))
ts = np.linspace(0.3, 0.99, 70)
for tag, lg, col in (('Crop named', named, 'tab:green'), ('Crop unknown', test_logits, 'tab:blue')):
    conf, pred = F.softmax(lg / T, 1).max(1); right = (pred == test_y).float()
    ax.plot(ts, [float((conf >= t).float().mean()) * 100 for t in ts], color=col, label=f'{tag}: coverage')
    ax.plot(ts, [float(right[conf >= t].mean()) * 100 if (conf >= t).any() else np.nan for t in ts], color=col, ls='--', label=f'{tag}: accuracy when accepted')
ax.axvline(thr_crop, color='grey', ls=':'); ax.axvline(0.85, color='crimson', ls=':'); ax.text(0.85, 5, ' server floor 0.85', color='crimson', fontsize=7)
ax.set_xlabel('Confidence threshold'); ax.set_ylabel('Percent'); ax.legend(fontsize=7, loc='lower left')
save(fig, 'c_cov')

cm = np.zeros((len(CK_LABELS), len(CK_LABELS)))
for t, p in zip(test_y.tolist(), pred_all.tolist()): cm[t, p] += 1
used = [i for i in range(len(CK_LABELS)) if cm[i].sum() > 0]
sub = cm[np.ix_(used, used)]; sub = sub / sub.sum(1, keepdims=True)
fig, ax = plt.subplots(figsize=(8.2, 7.4))
im = ax.imshow(sub, cmap='Greens', vmin=0, vmax=1)
short = [CK_LABELS[i].replace('|', ': ') for i in used]
ax.set_xticks(range(len(used))); ax.set_xticklabels(short, rotation=90, fontsize=5.5); ax.set_yticks(range(len(used))); ax.set_yticklabels(short, fontsize=5.5)
ax.set_xlabel('Predicted'); ax.set_ylabel('True'); ax.grid(False); fig.colorbar(im, ax=ax, fraction=0.04, label='Share of the true class')
save(fig, 'c_cm')
""")

md("""
## D. Optional: re-run the training to log the curve
Same recipe and seeds as the training notebook (cells copied). It takes about 30 minutes on a T4 and gives a training curve for `c_curve`. The run produces its own new weights and test numbers; the report states that the curve is from a re-run, and the served model stays `plant_disease_v3.pth`. Skip this section if you do not need the curve.
""")
src5 = orig[5]
src5 = src5.replace("best_acc, best_state = -1.0, None", "best_acc, best_state = -1.0, None\nhistory = []")
src5 = src5.replace("    print(f'epoch {epoch + 1}/{EPOCHS} loss={total:.2f} field_val_acc={val_acc:.3f}', flush=True)",
                    "    print(f'epoch {epoch + 1}/{EPOCHS} loss={total:.2f} field_val_acc={val_acc:.3f}', flush=True)\n    history.append((epoch + 1, total / len(train_dl), val_acc))")
assert "history.append" in src5 and "history = []" in src5
code(src5)
code(orig[6])
code("""
ep = [h[0] for h in history]; loss = [h[1] for h in history]; acc = [h[2] * 100 for h in history]
fig, ax = plt.subplots(figsize=(6.2, 3.5))
ax.plot(ep, loss, color='tab:blue', label='Training loss (mean per batch)'); ax.set_xlabel('Epoch'); ax.set_ylabel('Training loss')
ax2 = ax.twinx(); ax2.plot(ep, acc, color='tab:green', label='Field-photo validation accuracy'); ax2.set_ylabel('Validation accuracy (%)'); ax2.grid(False)
best_ep = int(np.argmax(acc)) + 1; ax2.axvline(best_ep, color='grey', ls=':'); ax2.text(best_ep, min(acc), f' best epoch {best_ep}', fontsize=8)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='center right')
save(fig, 'c_curve')
""")

md("## Download everything")
code("""
!cd /content && zip -qr report_figures.zip report_figures && ls report_figures
from google.colab import files
files.download('/content/report_figures.zip')
""")

# every code cell must at least parse (shell lines and magics removed)
for i, c in enumerate(cells):
    if c["cell_type"] == "code":
        text = "".join(c["source"])
        text = "\n".join("pass" if l.strip().startswith(("!", "%")) else l for l in text.split("\n"))
        try:
            ast.parse(text)
        except SyntaxError as e:
            raise SystemExit(f"cell {i} does not parse: {e}")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
(HERE / "dhartisense_report_figures.ipynb").write_text(json.dumps(nb, indent=1), encoding="utf8")
print("wrote", HERE / "dhartisense_report_figures.ipynb", "-", len(cells), "cells; all code cells parse")
