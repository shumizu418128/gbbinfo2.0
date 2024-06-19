FROM python:3.7.12-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt
RUN apt-get -y update
RUN apt-get -y upgrade

COPY . /app

CMD python run.py
