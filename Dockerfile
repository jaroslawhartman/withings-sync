FROM python:3.12-alpine

# Install python-lxml
RUN apk add --no-cache --virtual .build-deps \
    gcc musl-dev \
    libxslt-dev libxml2-dev && \
    pip install lxml setuptools && \
    apk del .build-deps && \
    apk add --no-cache libxslt libxml2

RUN mkdir -p /src
COPY . /src

RUN cd /src && \
    pip install .

ENTRYPOINT ["withings-sync"]
