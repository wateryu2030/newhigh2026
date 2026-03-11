FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY backtest-engine/ ./backtest-engine/
RUN pip install -e ./core -e ./backtest-engine
CMD ["python", "-c", "from backtest_engine import run_backtest; print('backtest-engine ok')"]
