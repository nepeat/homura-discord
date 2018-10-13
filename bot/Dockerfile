FROM python:3.7-alpine

# Edge repos
RUN echo http://dl-cdn.alpinelinux.org/alpine/edge/main > /etc/apk/repositories && \
    echo http://dl-cdn.alpinelinux.org/alpine/edge/community >> /etc/apk/repositories && \
    echo http://dl-cdn.alpinelinux.org/alpine/edge/testing >> /etc/apk/repositories

# Requirements
COPY requirements.txt /app/requirements.txt
RUN apk add --no-cache build-base libffi libffi-dev ca-certificates pkgconf ffmpeg opus opus-dev rtmpdump libsodium \
    libsodium-dev tini imagemagick && \
	SODIUM_INSTALL=system pip3 install -r /app/requirements.txt && \
	apk --no-cache del build-base opus-dev libffi-dev libsodium-dev

# Workdir
WORKDIR /app

# Add code
COPY . /app
RUN python3 setup.py install

# Tini entrypoint
ENTRYPOINT ["/sbin/tini", "--"]

CMD ["python3", "homura"]
