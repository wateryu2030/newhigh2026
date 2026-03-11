FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY ai-lab/ ./ai-lab/
RUN pip install -e ./core -e ./ai-lab
CMD ["python", "-c", "from ai_lab import generate_strategy; print('ai-lab ok')"]
