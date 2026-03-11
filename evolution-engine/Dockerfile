FROM python:3.11-slim
WORKDIR /app
COPY evolution-engine/ ./evolution-engine/
RUN pip install -e ./evolution-engine
CMD ["python", "-c", "from evolution_engine import StrategyPool, alpha_score; print('evolution-engine ok')"]
