#!/usr/bin/env sh

DOCKER_HOST="tcp://127.0.0.1:2376"
HASH=$(git log --pretty=format:'%h' -n 1)

docker-compose up -d --build

curl https://sentry.arquius.vm.thae.li/api/hooks/release/builtin/7/4f67a0e6cbfc3e57a41145a768c4278ad41b6aece08874768a6bf392e8380aac/ \
  -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"version\": \"$HASH\"}"
