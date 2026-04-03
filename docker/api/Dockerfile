FROM python:3.11-slim

WORKDIR /app/services/api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY services/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/api /app/services/api
COPY services/shared /app/services/shared
COPY configs /app/configs

ENV PYTHONPATH=/app/services/api:/app/services/shared

EXPOSE 8000

