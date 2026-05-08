FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        pkg-config \
        libffi-dev \
        libssl-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 appuser \
    && useradd -m -u 1000 -g appuser -s /bin/bash appuser

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir \
        --extra-index-url https://www.piwheels.org/simple \
        -r requirements.txt

COPY . /app/

RUN mkdir -p /app/logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "app:app"]
