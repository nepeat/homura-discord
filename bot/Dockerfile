FROM python:3.6.0-alpine

# Requirements
COPY requirements.txt /app/requirements.txt
RUN apk add --no-cache build-base libffi libffi-dev ca-certificates pkgconf ffmpeg opus opus-dev rtmpdump libsodium libsodium-dev && \
	SODIUM_INSTALL=system pip3 install -r /app/requirements.txt && \
	apk --no-cache del build-base opus-dev libffi-dev libsodium-dev

# Workdir
WORKDIR /app

# Add code
COPY . /app
RUN python3 setup.py install

CMD ["python3", "homura"]
