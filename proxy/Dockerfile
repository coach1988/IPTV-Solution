# syntax=docker/dockerfile:1

FROM python:3.9-slim

EXPOSE 8089/tcp

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY run.sh /app/run.sh
COPY *.py /app/

CMD [ "sh", "-c", "/app/run.sh"]
