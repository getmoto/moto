FROM python:2

ADD . /moto/
ENV PYTHONUNBUFFERED 1

WORKDIR /moto/
RUN python setup.py install

CMD ["moto_server"]

EXPOSE 5000
