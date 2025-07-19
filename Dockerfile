FROM python:3.13-alpine

ADD . /moto/
ENV PYTHONUNBUFFERED 1

WORKDIR /moto/
RUN  pip3 --no-cache-dir install --upgrade pip setuptools && \
     pip3 --no-cache-dir install --editable ".[server]"

# Install cURL
RUN  apk add --no-cache curl

ENTRYPOINT ["/usr/local/bin/moto_server", "-H", "0.0.0.0"]

EXPOSE 5000
