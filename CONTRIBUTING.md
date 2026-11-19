# Contributing

Thanks for helping. This project aims to give small farmers practical, honest advice, so accuracy and clear limits matter more than new features.

## Ways to help

- **Bug reports and ideas:** open an issue with what you did, what you expected and what happened (screenshots help; remove anything private).
- **Translations:** the Hindi, Marathi, Bengali and Tamil text in `static/ui.js` has not been reviewed by native speakers. Corrections are very welcome.
- **Agronomy review:** crop requirements, irrigation parameters (`ml/water_plan.py`) and fertiliser doses (`ml/nutrient_plan.py`) are generic. State-level corrections with a cited source are valuable.
- **Data:** better or newer open datasets for regional crop practice (the bundled one ends in 2015 and covers India only).

## Setting up

Follow the quick start in [README.md](README.md). Then:

```powershell
.\venv\Scripts\python.exe scripts\run_checks.py        # must pass before you open a pull request
```

## Pull requests

- Keep changes small and focused; explain the why.
- No secrets, keys, personal data, datasets or model weights in commits (`git status` and `git diff --staged` first).
- Add a self-check or test for new logic (see the `__main__` blocks at the bottom of `ml/*.py` and `app/*.py`).
- Any data or service you add must be free to redistribute or call, and listed with its licence in `NOTICE.md`.
- By contributing you agree your work is released under the project's MIT licence.

## Ground rules for advice features

Outputs are guidance, never guarantees: label estimates, show the data source, and say what the tool cannot know. Do not add yield, price or medical claims without evidence.
