FROM python:3.7-slim

ADD . /moto/
ENV PYTHONUNBUFFERED 1

ARG PORT=5000

WORKDIR /moto/
RUN  pip3 --no-cache-dir install --upgrade pip setuptools && \
     pip3 --no-cache-dir install ".[server]"

ENTRYPOINT ["/usr/local/bin/moto_server", "-H", "0.0.0.0", "-p", "${PORT}"]

EXPOSE 5000
