# syntax=docker/dockerfile:1

FROM python:3.11-alpine

WORKDIR /code/src
EXPOSE 5000

RUN apk add --no-cache alpine-sdk gcc musl-dev linux-headers g++ poetry python3-dev nodejs npm libffi-dev
COPY pyproject.toml poetry.lock ./
# werkzeug must be installed separately: workaround for https://github.com/getmoto/moto/issues/5341
RUN poetry run pip install werkzeug==2.2.3
RUN poetry install --only main --no-interaction
COPY schema.prisma ./
RUN poetry run prisma generate
COPY api ./api

CMD ["poetry", "run", "python", "-m", "api.app"]
