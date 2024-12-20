FROM python:3.12-alpine

ENV PROJECT="withings-sync" \
    PACKAGE="withings_sync"

RUN apk --no-cache add supercronic

RUN adduser -D $PROJECT

ENV PROJECT_DIR="/home/${PROJECT}"

USER $PROJECT
WORKDIR $PROJECT_DIR

ENV PATH="${PROJECT_DIR}/.poetry/bin:${PATH}" \
    PATH="${PROJECT_DIR}/.local/bin:${PATH}" \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME="${PROJECT_DIR}/.poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR="/tmp/poetry_cache"

RUN pip install poetry

COPY --chown=$PROJECT:$PROJECT pyproject.toml poetry.lock README.md $PROJECT_DIR/
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

COPY --chown=$PROJECT:$PROJECT $PACKAGE ./$PACKAGE/
RUN poetry install --without dev

ENTRYPOINT ["poetry", "run", "withings-sync"]
