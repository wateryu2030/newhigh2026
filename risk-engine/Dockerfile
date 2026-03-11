FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY risk-engine/ ./risk-engine/
RUN pip install -e ./core -e ./risk-engine
CMD ["python", "-c", "from risk_engine import should_disable_strategy_drawdown; print('risk-engine ok')"]
