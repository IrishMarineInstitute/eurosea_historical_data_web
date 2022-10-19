FROM python:3.10.6-alpine3.16

RUN apk add --no-cache build-base netcdf geos proj

RUN adduser \
    --disabled-password \
    --gecos "" \
    --no-create-home \
    --shell /bin/bash \
    uwsgi

COPY webapp /webapp

RUN chown -R uwsgi:uwsgi /webapp

USER uwsgi
WORKDIR /webapp
COPY requirements.txt requirements.txt
RUN pip3 install uwsgi
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5000
CMD ["uwsgi", "--enable-threads", "--http", ":5000", "--wsgi-file", "wsgi.py"]
