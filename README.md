# Mitotic Count Density Standardizer

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** CAP / CLSI / ISO Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

The Mitotic Count Density Standardizer standardizes raw mitotic counts per 10 High Power Fields (HPF) to mm² per microscope field diameter. It provides both single-case evaluation and batch CSV processing.

- **Author:** Dr. Abu Suraih Sakhri
- **License:** MIT

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`calculate_metrics()`**: Core domain algorithm that computes weighted scores and classifies results into clinical tiers (Low/Standard, Moderate/Intermediate, High/Severe).
- **`process_single()`** — Evaluates a single case via CLI arguments.
- **`process_batch()`** — Processes CSV input files with path-traversal protection.
- **`main()`** — CLI entry point with subcommands.

---

## 📐 Mathematical Formulation

```text
score = primary_val + sum(v_i * (1/i) for i, v_i in enumerate(secondary_vals, start=2))
rounded_score = round(score, 2)
```

**Classification Tiers:**
- **< 10.0** → Low / Standard (Standard monitoring)
- **10.0 – 25.0** → Moderate / Intermediate (Close observation)
- **≥ 25.0** → High / Severe (Urgent clinical intervention)

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/mitotic-count-density-standardizer.git
cd mitotic-count-density-standardizer

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[test]"
```

---

## 💻 CLI Quickstart & Usage

### 1. Single Case Evaluation
```bash
python mitotic_density.py single --v1 14.5 --v2 4.2 --v3 1.8
```

### 2. Batch CSV Processing
```bash
python mitotic_density.py batch -i sample.csv -o results.csv
```

### 3. Enterprise CLI (Agents System)
```bash
# Run audit evaluation
python cli.py audit --primary 28.5 --secondary 14.2

# Batch process records
python cli.py batch -i sample.csv -o results.csv

# Verify HMAC audit trail
python cli.py verify-audit

# Launch FastAPI REST server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference
- `--v1`: Primary measurement (default: 10.0)
- `--v2`: Secondary measurement (default: 5.0)
- `--v3`: Tertiary measurement (default: 2.0)
- `-i / --input`: Input CSV file path
- `-o / --output`: Output CSV file path (default: results.csv)

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary measurement | Required |
| `v2` | Secondary measurement | Required |
| `v3` | Tertiary measurement | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers from audit logs and outbound data.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition with integrity verification.
* **Path Traversal Protection:** File path validation preventing access to system directories.
* **Secure Key Management:** Audit signing key loaded from `AUDIT_SECRET_KEY` environment variable with secure random fallback.

### Environment Variables

| Variable | Description | Default |
|:---------|:------------|:--------|
| `AUDIT_SECRET_KEY` | HMAC-SHA256 audit signing key | Random (ephemeral) |
| `MODEL_PROVIDER` | LLM provider for chat (mock/ollama/claude/openai) | mock |

---

## 🧪 Testing & Verification

Run the full test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest -v --cov=mitotic_density --cov=agents
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

### Docker
```bash
# Set production audit key
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Build and run
docker build -t mitotic-count-density-standardizer .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY mitotic-count-density-standardizer
```

### Docker Compose
```bash
# Generate a secure key
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Launch
docker-compose up -d
```

---

## 📁 Project Structure

```
mitotic-count-density-standardizer/
├── agents/                  # Enterprise agent system
│   ├── api.py              # FastAPI REST server
│   ├── base.py             # Security, PHI guard, audit trail
│   ├── models.py           # Pydantic schemas
│   ├── supervisor.py       # Multi-agent orchestrator
│   ├── workers.py          # Specialized worker agents
│   └── ...
├── tests/                  # Test suite
│   ├── test_security.py    # Security & path validation tests
│   └── test_core.py        # Core functionality tests
├── mitotic_density.py      # Core domain algorithm
├── cli.py                  # Enterprise CLI entry point
├── enrichment.py           # Enrichment feature engines
├── simulator.py            # High-throughput stress tester
├── pyproject.toml          # Python package configuration
├── Dockerfile              # Container build
└── docker-compose.yml      # Container orchestration
```
