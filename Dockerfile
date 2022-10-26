FROM python:3.10.4-alpine AS build

RUN apk add --no-cache build-base linux-headers libxml2-dev libxslt-dev pcre-dev openssl-dev

COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

FROM python:3.10.4-alpine

RUN apk add --no-cache libxml2 libxslt pcre

COPY --from=build /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=build /usr/local/bin/* /usr/local/bin/

WORKDIR /app

COPY . /app/

RUN adduser -D -u 1001 appuser && \
  chown -R appuser:appuser /app

USER appuser

CMD ["uwsgi", "--ini", "uwsgi.ini", "--http", "0.0.0.0:8000", "-w", "server:app"]
