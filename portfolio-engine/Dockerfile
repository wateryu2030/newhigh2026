FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY portfolio-engine/ ./portfolio-engine/
RUN pip install -e ./core -e ./portfolio-engine
CMD ["python", "-c", "from portfolio_engine import equal_weight_weights; print('portfolio-engine ok')"]
