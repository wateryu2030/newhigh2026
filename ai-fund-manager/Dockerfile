FROM python:3.11-slim
WORKDIR /app
COPY evolution-engine/ ./evolution-engine/
COPY ai-fund-manager/ ./ai-fund-manager/
RUN pip install -e ./evolution-engine -e ./ai-fund-manager
CMD ["python", "-c", "from ai_fund_manager import allocate_capital; print('ai-fund-manager ok')"]
