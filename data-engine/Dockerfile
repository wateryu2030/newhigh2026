FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY data-engine/ ./data-engine/
RUN pip install -e ./core -e ./data-engine
CMD ["python", "-c", "from data_engine import fetch_klines; print('data-engine ok')"]
