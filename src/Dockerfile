# syntax=docker/dockerfile:1

FROM python:3-slim

WORKDIR /code/src
EXPOSE 5000

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://deb.nodesource.com/setup_19.x | bash - && \
    apt-get install -y nodejs
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main
COPY schema.prisma ./
RUN poetry run prisma generate
COPY api ./api

CMD ["poetry", "run", "python", "-m", "api.app"]
