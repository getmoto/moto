FROM python:2

ADD . /moto/
ENV PYTHONUNBUFFERED 1

WORKDIR /moto/
RUN pip install ".[server]"

CMD ["moto_server"]

EXPOSE 5000
