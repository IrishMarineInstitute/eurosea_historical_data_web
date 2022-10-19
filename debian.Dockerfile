FROM python:3.10-slim-bullseye

RUN apt-get update && \
    apt-get install -y python3-netcdf4
RUN apt-get install -y build-essential
RUN apt-get install -y libgeos-dev
RUN apt-get install -y libproj-dev

RUN useradd -ms /bin/bash uwsgi

COPY webapp /webapp

RUN chown -R uwsgi:uwsgi /webapp

USER uwsgi
WORKDIR /webapp
COPY requirements.txt requirements.txt
RUN pip3 install uwsgi
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5000
CMD ["uwsgi", "--enable-threads", "--http", ":5000", "--wsgi-file", "wsgi.py"]
