# Mitotic Count Density Standardizer

A calibrated, area-based **mitotic-count conversion** utility for pathology research and reporting. Converts observed mitotic figures into **mitoses/mm²** using either a measured circular high-power field (HPF) diameter or a directly assessed tissue area.

**Use the browser application:** Open [index.html](index.html) locally, or serve the repository using a static HTTP server. The repository advertises a GitHub Pages homepage, but live deployment has not yet been independently verified.

## Calculation

For non-overlapping fully assessed circular fields, each with calibrated diameter `d` millimetres:

```text
area_per_HPF_mm2 = π × (d / 2)²
total_area_mm2   = area_per_HPF_mm2 × number_of_HPF_counted
mitoses_per_mm2  = observed_mitotic_count / total_area_mm2
```

For digital pathology or irregular examined regions, provide the measured **total tissue area in mm²** directly instead of computing it from field diameter. Exactly one area source must be provided.

The tool reports an unrounded floating-point density; users should apply the reporting and rounding conventions specified by their relevant tumour protocol. **There are no generic clinical risk tiers or treatment recommendations.** For example, the ICCR breast reporting dataset requires calibration and uses tumour-specific mitotic grading rules; a density conversion alone does not assign a histological grade.

## Browser interface

- Single-case conversion with input validation and a transparent area breakdown.
- CSV batch conversion, preserving specimen metadata and exporting computed columns.
- Runs entirely in browser JavaScript. No Pyodide download or server-side Python process is required.
- Uploaded CSV data stays in the browser session; no upload endpoint is used. No browser local-storage persistence.
- CSV inputs are limited to 2 MB / 10,000 records to reduce browser resource exhaustion.

Open the repository's `index.html` in a modern Chromium-, Firefox-, or Safari-based browser. The source is also mirrored under `docs/` and `web/` for common static hosting configurations. JavaScript syntax is checked in the test suite when Node.js is available.

## Python installation and CLI

Requires Python 3.10 or later.

```bash
python -m pip install -e ".[test]"
mitotic-density single --mitotic-count 12 --field-diameter-mm 0.55 --fields-counted 10
mitotic-density single --mitotic-count 6 --measured-area-mm2 2.0
mitotic-density batch -i sample.csv -o results.csv
pytest -q
```

The standard CSV schema uses `mitotic_count`, and either `field_diameter_mm` or `measured_area_mm2`; `fields_counted` is optional (default: 10). Extra columns, such as a non-identifying `specimen_id`, are preserved. Rows with missing or invalid measurements cause explicit errors; no partial output is published.

For direct Python calls:

```python
from mitotic_density import calculate_metrics

result = calculate_metrics(mitotic_count=12, field_diameter_mm=0.55, fields_counted=10)
print(result["mitoses_per_mm2"])
```

The historical `score` output alias now equals **mitoses/mm²**, not the earlier arbitrary weighted score. Prior `v1/v2/v3` input formats are intentionally discontinued because they did not express mitotic density.

## REST API (optional)

```bash
mitotic-agent serve --host 127.0.0.1 --port 8000
```

- `GET /` serves the browser UI from a source checkout.
- `POST /api/density` accepts `{"mitotic_count":12,"field_diameter_mm":0.55,"fields_counted":10}` and returns area and density.
- `GET /health` and `GET /metrics` report process-local service information.
- The old `/api/audit` and `/api/chat` interfaces remain **demonstration-only**. Their thresholds, mock agent responses and classifications are **not validated clinical decision support**.

The supplementary `enrichment.py` modules are historical placeholders; they do not implement real FHIR integration, patient stratification or cross-institutional analytics. They must not be used to make patient decisions.

## Privacy and security

The browser calculator processes numeric inputs and CSV content locally. Do not submit patient-identifying data to the optional FastAPI service. Its identifier-pattern screening is **not comprehensive de-identification** and does not establish HIPAA compliance. The in-memory audit chain uses HMAC-SHA256 and verifies entry signatures and chain continuity, but is **not persistent across restarts**. For stable signing across restarts, configure `AUDIT_SECRET_KEY` before starting the API.

CSV exports escape formula-like content in user-supplied cells. Server deployments require their own authentication, access controls, TLS, persistence and privacy review before use with sensitive information.

## Development and containers

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m compileall -q mitotic_density.py cli.py agents
python -m build  # if the build package is installed
```

The included `Dockerfile` and `docker-compose.yml` run the optional FastAPI server. GitHub Actions runs unit tests on Python 3.10–3.12. No server runtime is required for the static browser interface.

## Scientific background

- [ICCR: Histological tumour grade (invasive breast cancer)](https://www.iccr-cancer.org/datasets/docs/iccr-invasive-histotg/) — calibrated HPF area and specimen-specific scoring.
- [ICCR melanoma reporting guidance](https://pmc.ncbi.nlm.nih.gov/articles/PMC3864181/) — area-normalized mitotic counting and site-specific methodology.

This utility performs a numerical conversion, not an interpretation of field selection, biopsy adequacy, reporting conventions, prognosis, or treatment.

**License:** [MIT](LICENSE).
