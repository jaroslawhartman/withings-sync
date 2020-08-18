FROM python:3.8-alpine

RUN apk add --update --no-cache libxml2-dev libxslt-dev gcc musl-dev

# Profit from Docker build cache buy building python lxml here..
RUN pip3 install lxml requests

RUN mkdir -p /src
COPY . /src

RUN cd /src && \
    python3 ./setup.py install

ENTRYPOINT ["withings-sync"]
