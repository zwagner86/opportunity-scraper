FROM python:3.11-slim

WORKDIR /app/services/dashboard

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY services/dashboard/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/dashboard /app/services/dashboard
COPY services/shared /app/services/shared

ENV PYTHONPATH=/app/services/dashboard:/app/services/shared

EXPOSE 8501

