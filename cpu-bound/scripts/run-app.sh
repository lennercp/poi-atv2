#!/usr/bin/env bash
# Starts the application with the values in config/app.env.
# Build first: ./mvnw package
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
source config/app.env
set +a
exec java $JAVA_OPTS -jar target/cpu-bound.jar
