FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
COPY scheduler/ ./scheduler/
RUN pip install -e ./core -e ./scheduler
CMD ["python", "-c", "from scheduler import connect_pipeline; print('scheduler ok')"]
