FROM alpine:3.6

ADD . /moto/
ENV PYTHONUNBUFFERED 1

WORKDIR /moto/
RUN  apk add --no-cache python3 && \
     python3 -m ensurepip && \
     rm -r /usr/lib/python*/ensurepip && \
     pip3 --no-cache-dir install --upgrade pip setuptools && \
     pip3 --no-cache-dir install ".[server]"

ENTRYPOINT ["/usr/bin/moto_server", "-H", "0.0.0.0"]

EXPOSE 5000
