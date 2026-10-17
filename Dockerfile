FROM debian:bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-tk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Aceestver.py .

CMD ["python3", "Aceestver.py"]
