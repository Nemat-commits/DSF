#!/usr/bin/env bash
# Reproduce data, models, figures, reports and tests (does not start the server).
set -euo pipefail
export PYTHONPATH=src
.venv/bin/python -m dsf.generate_data
.venv/bin/python -m dsf.features
.venv/bin/python -m dsf.train
.venv/bin/python -m dsf.make_reports
.venv/bin/python -m pytest -q
