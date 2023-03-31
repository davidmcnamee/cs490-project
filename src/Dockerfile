# syntax=docker/dockerfile:1

FROM python:3.11-alpine

WORKDIR /code/src
ENV FLASK_APP=api/app.py
ENV FLASK_RUN_HOST=0.0.0.0
EXPOSE 5000

RUN apk add --no-cache alpine-sdk gcc musl-dev linux-headers g++ poetry python3-dev nodejs npm libffi-dev
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main
COPY schema.prisma ./
RUN poetry run prisma generate
COPY api ./api

CMD ["poetry", "run", "python", "-m", "api.app"]
