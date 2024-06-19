FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt
RUN apt-get -y update
RUN apt-get -y upgrade

COPY . /app

EXPOSE 8080

CMD python run.py
