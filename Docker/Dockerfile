FROM alpine as git

RUN apk update && apk add git openssh-client

ARG SSH_PRIVATE_KEY

RUN mkdir ~/.ssh/ && \
    echo "$SSH_PRIVATE_KEY" >> ~/.ssh/id_rsa && \
    chmod 600 ~/.ssh/id_rsa && \
    touch ~/.ssh/known_hosts && \
    ssh-keyscan github.com >> ~/.ssh/known_hosts

RUN git clone git@github.com:jaroslawhartman/withings-garmin-v2.git

FROM python:3.6-alpine

RUN mkdir -p /withings-garmin-v2
COPY --from=git /withings-garmin-v2 /withings-garmin-v2

RUN pip install --upgrade pip && \
    pip install requests

WORKDIR /withings-garmin-v2

ENTRYPOINT ["./sync.py"]
CMD ["-h"]
