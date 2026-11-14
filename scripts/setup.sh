#!/usr/bin/env bash
set -e

echo "=== Setting up Omnichannel Ticket Routing & SLA Platform ==="

# 1. Install Backend Dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt || pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy psycopg2-binary alembic pandas numpy scikit-learn pytest

# 2. Build Frontend
echo "Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# 3. Generate Starter Dataset
echo "Generating Deterministic Synthetic Dataset (Seed 20261022)..."
python generate_data.py --seed 20261022 --scale starter

# 4. Seed Database
echo "Seeding Persistence Store..."
python scripts/seed.py

# 5. Run Validation
echo "Running Validation..."
python scripts/validate.py

# 6. Run Pytest
echo "Running Test Suites..."
pytest backend/tests/test_omnichannel_routing.py -v

echo "=== Setup Complete! Start server with: python -m uvicorn backend.app.main:app --port 8000 ==="
