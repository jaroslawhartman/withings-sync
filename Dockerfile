FROM python:3.9 AS sync-build

COPY . /workdir/

WORKDIR /workdir
RUN pip3 install -r requirements.txt
RUN python3 setup.py bdist_wheel


FROM python:3.9 AS sync

COPY --from=sync-build /workdir/dist/withings_sync-*.whl /tmp/
RUN pip3 install /tmp/withings_sync-*.whl

WORKDIR /root
ENTRYPOINT ["/usr/bin/withings-sync"]
