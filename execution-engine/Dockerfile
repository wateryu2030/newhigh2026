FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY execution-engine/ ./execution-engine/
RUN pip install -e ./core -e ./execution-engine
CMD ["python", "-c", "from execution_engine import place_order; print('execution-engine ok')"]
