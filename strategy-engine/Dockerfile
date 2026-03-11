FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY strategy-engine/ ./strategy-engine/
RUN pip install -e ./core -e ./strategy-engine
CMD ["python", "-c", "from strategy_engine import trend_following_signals; print('strategy-engine ok')"]
