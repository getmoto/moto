FROM python:3.7-slim

ADD . /moto/
ENV PYTHONUNBUFFERED 1

WORKDIR /moto/
RUN  pip3 --no-cache-dir install --upgrade pip setuptools && \
     pip3 --no-cache-dir install ".[server]" && \
     python3 setup.py develop && \
     pip3 --no-cache-dir install -r requirements-dev.txt && \
     apt update && apt install make

CMD ["python3", "/moto/moto/server.py", "-H", "0.0.0.0"]

EXPOSE 5000
