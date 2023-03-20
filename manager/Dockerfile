# syntax=docker/dockerfile:1

FROM python:3.9-slim

EXPOSE 8088/tcp

WORKDIR /app
VOLUME ["/app/database/"]
VOLUME ["/app/staticfiles/"]

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY run.sh /app/run.sh
COPY iptvmanager/ /app/iptvmanager/
COPY *.py /app/
COPY manager/ /app/manager/
COPY lib/ /app/lib/

CMD [ "sh", "-c", "/app/run.sh"]
