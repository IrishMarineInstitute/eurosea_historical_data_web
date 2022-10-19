FROM python:3.10.6-alpine3.16

RUN apk add --no-cache build-base netcdf geos proj
RUN apk add linux-headers pcre pcre-dev libffi libffi-dev openssl-dev
RUN apk add hdf5 hdf5-dev netcdf-dev

RUN pip3 install --upgrade pip
RUN pip3 install uwsgi
RUN apk add geos-dev proj-dev 
RUN apk add proj-util

RUN pip3 install Cython

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

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

EXPOSE 5000
CMD ["uwsgi", "--enable-threads", "--http", ":5000", "--wsgi-file", "wsgi.py"]
