FROM debian:bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-tk \
        python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir fpdf2

ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

COPY Aceestver.py .

CMD ["python3", "Aceestver.py"]
