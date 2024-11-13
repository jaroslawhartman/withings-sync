FROM python:3.12-alpine

RUN adduser -D withings-sync

USER withings-sync
WORKDIR /home/withings-sync

ENV PATH="/home/withings-sync/.poetry/bin:${PATH}" \
    PATH="/home/withings-sync/.local/bin:${PATH}" \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME=/home/withings-sync/.poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry

COPY --chown=withings-sync:withings-sync pyproject.toml poetry.lock README.md .VERSION ./
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

COPY --chown=withings-sync:withings-sync withings_sync ./withings_sync/
RUN poetry install --without dev

ENTRYPOINT ["poetry", "run", "withings-sync"]
