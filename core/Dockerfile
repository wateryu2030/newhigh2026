FROM python:3.11-slim
WORKDIR /app
COPY core/ ./core/
RUN pip install -e ./core
CMD ["python", "-c", "from core import OHLCV, Signal; print('core ok')"]
