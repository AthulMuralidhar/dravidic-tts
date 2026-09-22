# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md LICENSE constraints.txt ./
COPY src ./src
RUN python -m pip install --prefix=/install --constraint constraints.txt .

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DRAVIDIC_TTS_HOST=0.0.0.0 \
    DRAVIDIC_TTS_PORT=8000 \
    DRAVIDIC_TTS_PROVIDER=espeak \
    DRAVIDIC_TTS_MAX_CHARACTERS=5000

RUN apt-get update \
    && apt-get install --yes --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

COPY --from=builder /install /usr/local

USER app
WORKDIR /home/app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)); assert data['status']=='ok'"]

CMD ["uvicorn", "dravidic_tts.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
