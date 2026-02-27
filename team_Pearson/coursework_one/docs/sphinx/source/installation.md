# Installation Guide

## Prerequisites
- Python 3.11+
- Poetry 2.x
- Docker Desktop with Docker Compose

## 1. Start shared infrastructure
Run from repository root:

```bash
cd /Users/celiawong/Desktop/ift_coursework_2025
docker compose up -d postgres_db mongo_db miniocw
```

## 2. Install project dependencies

```bash
cd team_Pearson/coursework_one
poetry install
```

## 3. Verify toolchain

```bash
poetry run pytest -q
poetry run bandit -r modules Main.py
```

## 4. Build docs

```bash
cd docs/sphinx
poetry run make html
```

Generated HTML entry point:
`docs/sphinx/build/html/index.html`
