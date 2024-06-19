FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . /app

RUN ls -l /app/app

EXPOSE 8080

CMD ["python", "run.py"]
