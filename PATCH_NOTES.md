# Global EV Infra — Production Patch v1.0.4

This patch hardens the **global-ev-infra-dataset** repo with:

- ✅ Dataset validator (syntax fixed) + optional strict mode
- ✅ Derived views builder (writes generated/*.csv)
- ✅ SHA256 checksum writer
- ✅ Ruff config that ignores notebooks/examples/generated (so CI stays green)
- ✅ GitHub Actions workflow for lint + validation + views

## Apply
Copy these files/folders into your repo root (overwrite when prompted):

- `.github/`
- `scripts/`
- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt`
- `data_dictionary.csv`
- `.gitignore` (merge if you already have one)

## Run
```bash
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

python -m ruff check scripts --fix
python -m ruff format scripts
python -m ruff check scripts

python scripts\validate_dataset.py --data-dir data
python scripts\validate_dataset.py --data-dir data --strict

python scripts\build_views.py --data-dir data --out-dir generated
python scripts\write_checksums.py --root . --out checksums.sha256
```


## v1.0.4
- Fix: GitHub Actions workflow YAML (no placeholders)
