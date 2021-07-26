FROM python:3.7-buster

ADD . /moto/
ENV PYTHONUNBUFFERED 1
WORKDIR /moto/
RUN make init
RUN make test