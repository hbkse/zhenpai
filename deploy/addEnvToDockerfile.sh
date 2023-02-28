#!/usr/bin/env bash
for envkey in "$@"
do
  value="$(printenv $envkey)"
  sed -i -e "/^# Environment Variables/a ENV $envkey $value" Dockerfile
done