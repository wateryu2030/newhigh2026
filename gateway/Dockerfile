FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY data-pipeline/ ./data-pipeline/
COPY backtest-engine/ ./backtest-engine/
COPY risk-engine/ ./risk-engine/
COPY execution-engine/ ./execution-engine/
COPY gateway/ ./gateway/
COPY openclaw_engine/ ./openclaw_engine/
RUN pip install -e ./core -e ./data-pipeline -e ./backtest-engine -e ./risk-engine -e ./execution-engine -e ./gateway
ENV PYTHONPATH="/app/data-pipeline/src:/app/backtest-engine/src:/app/risk-engine/src:/app/execution-engine/src:/app/openclaw_engine:/app/core/src"
EXPOSE 8000
CMD ["uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
