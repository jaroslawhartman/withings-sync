FROM python:3.9

RUN apt-get update && \
	apt-get install -y \
		python3-lxml \
        # downgrade charset-normalizer, because requests need version 2.0
        && pip install -Iv charset-normalizer==2.0.0

RUN mkdir -p /src
COPY . /src

RUN cd /src && \
    python3 ./setup.py install

ENTRYPOINT ["withings-sync"]
