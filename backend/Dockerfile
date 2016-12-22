FROM python:3.6.0rc2-alpine

# Update packages and install setup requirements.
RUN apk --no-cache upgrade && \
	apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing gcc musl-dev postgresql-dev ca-certificates && \
	update-ca-certificates && \
	rm -rf /var/cache/apk/*

# Set WORKDIR to /src
WORKDIR /src

# Add and install Python modules
COPY requirements.txt /src/requirements.txt
RUN pip3 install -r requirements.txt

# Bundle app source
COPY . /src

# Install main module
RUN python3 setup.py install

# Expose web port
EXPOSE 5000

# Command
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-k", "gevent", "-w", "4", "disquotes:app"]
