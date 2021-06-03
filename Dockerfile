FROM python:3.9

RUN apt-get update && \
	apt-get install -y \
		python3-lxml

RUN mkdir -p /src
COPY . /src

RUN cd /src && \
    python3 ./setup.py install

ENTRYPOINT ["withings-sync"]
