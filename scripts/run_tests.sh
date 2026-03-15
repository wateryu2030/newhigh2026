#!/usr/bin/env bash
# Run all module tests (OpenClaw validation: must_pass_tests)
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
echo "Running core/tests..."
python -m pytest core/tests/ -v --tb=short -q
echo "Running data-engine/tests..."
python -m pytest data-engine/tests/ -v --tb=short -q
echo "Running evolution-engine/tests..."
python -m pytest evolution-engine/tests/ -v --tb=short -q
echo "Running strategy-engine/tests..."
python -m pytest strategy-engine/tests/ -v --tb=short -q
echo "Running portfolio-engine/tests..."
python -m pytest portfolio-engine/tests/ -v --tb=short -q
echo "Running risk-engine/tests..."
python -m pytest risk-engine/tests/ -v --tb=short -q
echo "Running scheduler/tests..."
python -m pytest scheduler/tests/ -v --tb=short -q
echo "Running gateway/tests..."
python -m pytest gateway/tests/ -v --tb=short -q
echo "Running evolution-stage (alpha-factory, alpha-scoring, strategy-evolution, simulation-world, meta-fund-manager, openclaw_engine)..."
python -m pytest alpha-factory/tests/ -v --tb=short -q
python -m pytest alpha-scoring/tests/ -v --tb=short -q
python -m pytest strategy-evolution/tests/ -v --tb=short -q
python -m pytest simulation-world/tests/ -v --tb=short -q
python -m pytest meta-fund-manager/tests/ -v --tb=short -q
python -m pytest openclaw_engine/tests/ -v --tb=short -q
echo "Running ai-models/tests..."
python -m pytest ai-models/tests/ -v --tb=short -q
echo "Running backtest-engine/tests..."
python -m pytest backtest-engine/tests/ -v --tb=short -q
echo "Running execution-engine/tests..."
python -m pytest execution-engine/tests/ -v --tb=short -q
echo "Running market-scanner/tests..."
python -m pytest market-scanner/tests/ -v --tb=short -q
echo "All tests passed."
