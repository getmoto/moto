FROM python:3.11-slim

# Install cURL
RUN  apt-get update && \
     apt-get install -y curl && \
     rm -rf /var/lib/apt/lists/*

ADD . /moto/
ENV PYTHONUNBUFFERED 1

WORKDIR /moto/
RUN  pip3 --no-cache-dir install --upgrade pip setuptools && \
     pip3 --no-cache-dir install ".[server]"


ENTRYPOINT ["/usr/local/bin/moto_server", "-H", "0.0.0.0"]

EXPOSE 5000
