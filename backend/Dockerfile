# Luphina API and worker (same image, different command)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LUPHINA_DATA_DIR=/data

WORKDIR /app

RUN useradd --create-home --uid 10001 luphina \
    && mkdir -p /data/output \
    && chown -R luphina /data

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY data/sample ./data/sample
RUN pip install --no-deps .

USER luphina
EXPOSE 8000

# Run migrations as a separate deploy step: `alembic upgrade head`
CMD ["uvicorn", "luphina.api.app:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
