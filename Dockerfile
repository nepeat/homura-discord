FROM alpine:edge

# Requirements
COPY requirements.txt /app/requirements.txt
RUN apk add --update build-base python3 python3-dev libffi libffi-dev ca-certificates libsodium libsodium-dev && \
	SODIUM_INSTALL=system pip3 install -r /app/requirements.txt && \
	apk del build-base opus-dev libffi-dev libsodium-dev && \
	rm -rf /var/cache/apk/*

# Workdir
WORKDIR /app

# Add code
COPY . /app
RUN python3 setup.py install

CMD ["python3", "nepeatbot"]
