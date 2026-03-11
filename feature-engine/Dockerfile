FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY feature-engine/ ./feature-engine/
RUN pip install -e ./core -e ./feature-engine
CMD ["python", "-c", "from feature_engine import build_feature_matrix; print('feature-engine ok')"]
